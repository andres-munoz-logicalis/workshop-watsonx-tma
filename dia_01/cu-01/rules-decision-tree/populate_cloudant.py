"""
Carga el árbol de decisión desde decision_tree.yaml a Cloudant (schema v2).

Uso:
    python populate_cloudant.py                         # carga decision_tree.yaml
    python populate_cloudant.py --file otro.yaml        # carga otro archivo
    python populate_cloudant.py --validate              # solo valida, no carga
    python populate_cloudant.py --version v1.2.0        # version explícita

Características:
  - Valida contra el schema v2 (summary, why_factors, pricing, handoff)
  - Genera un doc 'tree_metadata' con version + hash + timestamp, consultable
    desde el endpoint GET /metadata de la API
  - Usa ibmcloudant (consistente con main.py)
  - Usa bulk insert para velocidad
"""

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import os
import yaml
from dotenv import load_dotenv

from ibmcloudant.cloudant_v1 import CloudantV1, BulkDocs
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

load_dotenv()

CLOUDANT_URL    = os.environ["CLOUDANT_URL"]
CLOUDANT_APIKEY = os.environ["CLOUDANT_APIKEY"]
DB_NAME         = os.getenv("CLOUDANT_DB", "decision_tree")

METADATA_DOC_ID = "tree_metadata"
ALLOWED_TYPES   = {"question", "deep_dive", "result"}
DEPRECATED_RESULT_FIELDS = {"why", "pricing_model", "triggers_cu02", "params_cu02"}


# ==========================================================
# Validación (schema v2)
# ==========================================================

def validate(nodes: list) -> list:
    """Retorna lista de errores. Lista vacía = todo ok."""
    errors: list[str] = []
    ids = {n.get("_id") for n in nodes if "_id" in n}

    for node in nodes:
        nid = node.get("_id", "?")

        if "_id" not in node:
            errors.append("[?] Falta campo '_id'")
            continue
        if nid.startswith("_"):
            errors.append(f"[{nid}] Los IDs no pueden empezar con '_' (reservado por Cloudant)")
        if nid == METADATA_DOC_ID:
            errors.append(f"[{nid}] '{METADATA_DOC_ID}' es un ID reservado por el sistema")

        ntype = node.get("type")
        if ntype not in ALLOWED_TYPES:
            errors.append(f"[{nid}] 'type' debe ser uno de {sorted(ALLOWED_TYPES)}, encontrado: {ntype!r}")
            continue

        if ntype == "question":
            _validate_question(node, nid, ids, errors)
        elif ntype == "deep_dive":
            _validate_deep_dive(node, nid, ids, errors)
        elif ntype == "result":
            _validate_result(node, nid, errors)

    if "node_start" not in ids:
        errors.append("Falta el nodo raíz 'node_start'")

    return errors


def _validate_question(node: dict, nid: str, ids: set, errors: list):
    for field in ("question", "options"):
        if field not in node:
            errors.append(f"[{nid}] Falta campo '{field}'")
    options = node.get("options") or []
    if not options:
        errors.append(f"[{nid}] 'options' está vacío")
    for i, opt in enumerate(options):
        if "label" not in opt:
            errors.append(f"[{nid}] option[{i}] sin 'label'")
        if "next" not in opt:
            errors.append(f"[{nid}] option[{i}] sin 'next'")
        elif opt["next"] not in ids:
            errors.append(
                f"[{nid}] option[{i}] 'next' apunta a '{opt['next']}' que no existe"
            )


def _validate_deep_dive(node: dict, nid: str, ids: set, errors: list):
    for field in ("service", "next", "sections"):
        if field not in node:
            errors.append(f"[{nid}] Falta campo '{field}'")
    if node.get("next") and node["next"] not in ids:
        errors.append(f"[{nid}] 'next' apunta a '{node['next']}' que no existe")
    sections = node.get("sections") or []
    if not sections:
        errors.append(f"[{nid}] 'sections' está vacío")
    for i, section in enumerate(sections):
        if "section" not in section:
            errors.append(f"[{nid}] section[{i}] sin nombre")
        questions = section.get("questions") or []
        if not questions:
            errors.append(f"[{nid}] section[{i}] sin preguntas")
        for j, q in enumerate(questions):
            for field in ("id", "text"):
                if field not in q:
                    errors.append(f"[{nid}] section[{i}].question[{j}] sin '{field}'")


def _validate_result(node: dict, nid: str, errors: list):
    # Schema v2
    required = ("service", "summary", "why_factors", "key_considerations",
                "pricing", "docs_url", "handoff")
    for field in required:
        if field not in node:
            errors.append(f"[{nid}] Falta campo '{field}' (schema v2)")

    # Tipos
    if not isinstance(node.get("why_factors"), list):
        errors.append(f"[{nid}] 'why_factors' debe ser una lista")
    if not isinstance(node.get("key_considerations"), list):
        errors.append(f"[{nid}] 'key_considerations' debe ser una lista")
    if not isinstance(node.get("pricing"), dict):
        errors.append(f"[{nid}] 'pricing' debe ser un dict")
    else:
        for field in ("model", "notes"):
            if field not in node["pricing"]:
                errors.append(f"[{nid}] 'pricing.{field}' es requerido")
    if not isinstance(node.get("handoff"), dict):
        errors.append(f"[{nid}] 'handoff' debe ser un dict (puede ser {{}} si no hay siguiente agente)")

    # Campos deprecados
    for deprecated in DEPRECATED_RESULT_FIELDS:
        if deprecated in node:
            errors.append(
                f"[{nid}] campo '{deprecated}' es del schema viejo — "
                f"revisá la migración al schema v2"
            )


# ==========================================================
# Versionado
# ==========================================================

def compute_hash(yaml_path: Path) -> str:
    """Hash SHA-256 corto (12 chars) del contenido del YAML."""
    return hashlib.sha256(yaml_path.read_bytes()).hexdigest()[:12]


def build_metadata(nodes: list, version: str, file_hash: str, yaml_file: str) -> dict:
    counts = {
        "question":  sum(1 for n in nodes if n["type"] == "question"),
        "deep_dive": sum(1 for n in nodes if n["type"] == "deep_dive"),
        "result":    sum(1 for n in nodes if n["type"] == "result"),
    }
    return {
        "_id": METADATA_DOC_ID,
        "type": "metadata",
        "version": version,
        "hash": file_hash,
        "loaded_at": datetime.now(timezone.utc).isoformat(),
        "yaml_file": yaml_file,
        "node_count": len(nodes),
        "counts": counts,
    }


# ==========================================================
# Cloudant
# ==========================================================

def get_client() -> CloudantV1:
    auth = IAMAuthenticator(CLOUDANT_APIKEY)
    client = CloudantV1(authenticator=auth)
    client.set_service_url(CLOUDANT_URL)
    return client


def ensure_db(client: CloudantV1) -> bool:
    """True si creó la DB, False si ya existía."""
    try:
        client.get_database_information(db=DB_NAME).get_result()
        return False
    except Exception as e:
        if "404" in str(e) or "not_found" in str(e).lower():
            client.put_database(db=DB_NAME).get_result()
            return True
        raise


def purge_docs(client: CloudantV1, keep_events: bool = True):
    """
    Borra todos los docs del árbol (nodes + metadata). Si keep_events=True,
    preserva los docs type=event (telemetría) para no perder histórico.
    """
    resp = client.post_all_docs(db=DB_NAME, include_docs=keep_events).get_result()
    to_delete = []
    for row in resp.get("rows", []):
        doc_id = row["id"]
        if doc_id.startswith("_design/"):
            continue
        if keep_events:
            doc = row.get("doc") or {}
            if doc.get("type") == "event":
                continue
        to_delete.append({
            "_id": doc_id,
            "_rev": row["value"]["rev"],
            "_deleted": True,
        })
    if to_delete:
        client.post_bulk_docs(
            db=DB_NAME,
            bulk_docs=BulkDocs(docs=to_delete),
        ).get_result()
        print(f"  {len(to_delete)} documentos anteriores eliminados (eventos preservados)")
    else:
        print("  nada para eliminar")


def bulk_insert(client: CloudantV1, nodes: list, metadata: dict):
    all_docs = nodes + [metadata]
    resp = client.post_bulk_docs(
        db=DB_NAME,
        bulk_docs=BulkDocs(docs=all_docs),
    ).get_result()

    errors = [r for r in resp if isinstance(r, dict) and r.get("error")]
    if errors:
        print("\nErrores al insertar:")
        for e in errors:
            print(f"  x {e.get('id')}: {e.get('error')} — {e.get('reason')}")
        sys.exit(1)
    print(f"  {len(nodes)} nodos + metadata insertados correctamente")


def load_to_cloudant(nodes: list, metadata: dict):
    print(f"\nConectando a Cloudant: {CLOUDANT_URL}")
    client = get_client()

    if ensure_db(client):
        print(f"DB '{DB_NAME}' creada")
    else:
        print(f"DB '{DB_NAME}' existe — purgando documentos anteriores...")
        purge_docs(client, keep_events=True)

    print(f"\nInsertando {len(nodes)} nodos + metadata...")
    bulk_insert(client, nodes, metadata)

    print(f"\n{'─' * 55}")
    print(f"  version     : {metadata['version']}")
    print(f"  hash        : {metadata['hash']}")
    print(f"  loaded_at   : {metadata['loaded_at']}")
    print(f"  node_count  : {metadata['node_count']}")
    print(f"  counts      : {metadata['counts']}")
    print(f"{'─' * 55}")
    print("Listo. Podés verificar la versión con: curl $API/metadata")


# ==========================================================
# Main
# ==========================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file",    default="decision_tree.yaml", help="Archivo YAML con los nodos")
    parser.add_argument("--validate", action="store_true", help="Solo valida el YAML, no carga a Cloudant")
    parser.add_argument("--version",  default=None, help="Versión explícita (default: auto-<hash>)")
    args = parser.parse_args()

    yaml_path = Path(args.file)
    print(f"Leyendo {yaml_path}...")
    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    nodes = data.get("nodes", [])
    print(f"  {len(nodes)} nodos encontrados")

    errors = validate(nodes)
    if errors:
        print("\nErrores de validación:")
        for e in errors:
            print(f"  x {e}")
        sys.exit(1)
    print("  Validación OK (schema v2)")

    file_hash = compute_hash(yaml_path)
    version = args.version or f"auto-{file_hash}"
    metadata = build_metadata(nodes, version, file_hash, yaml_path.name)
    print(f"  version: {version}")
    print(f"  hash:    {file_hash}")

    if args.validate:
        print("\nModo --validate: no se cargó nada.")
        return

    load_to_cloudant(nodes, metadata)


if __name__ == "__main__":
    main()
