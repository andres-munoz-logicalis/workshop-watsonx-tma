import os
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from elasticsearch import Elasticsearch


def resolve_path(value: str, project_root: Path) -> str:
    """Resuelve una ruta del .env relativa a la raíz del proyecto."""
    if not value:
        return value
    p = Path(value)
    if p.is_absolute():
        return str(p)
    return str(project_root / p)


def main():
    print("Ejercicio 03 — Elasticsearch: Conexión y primera búsqueda")
    print("=" * 60)

    # ----- 1. Credenciales -----
    print("\n[1/6] Cargando credenciales...")

    dotenv_path = find_dotenv(usecwd=True)
    load_dotenv(dotenv_path)
    project_root = Path(dotenv_path).parent if dotenv_path else Path.cwd()

    ES_URL      = os.getenv("ES_URL", "")
    ES_USER     = os.getenv("ES_USER", "elastic")
    ES_PASSWORD = os.getenv("ES_PASSWORD", "")
    ES_INDEX    = os.getenv("ES_INDEX", "workshop_docs")
    ES_CA_CERT  = resolve_path(os.getenv("ES_CA_CERT", "certs/ca.crt"), project_root)

    if not (ES_URL and ES_PASSWORD):
        print("Faltan credenciales de Elastic en .env")
        sys.exit(1)
    if not os.path.isfile(ES_CA_CERT):
        print(f"No encuentro el cert en {ES_CA_CERT}")
        sys.exit(1)

    print("      Credenciales OK")
    print(f"      Cert: {ES_CA_CERT}")

    # ----- 2. Conectar al cluster -----
    print("\n[2/6] Conectando al cluster...")
    # Usamos ca_certs apuntando al certificado del cluster
    # (montado en /app/certs dentro del contenedor)

    es = Elasticsearch(
        ES_URL,
        basic_auth=(ES_USER, ES_PASSWORD),
        ca_certs=ES_CA_CERT
    )

    if es.ping():
        print("Conectado al cluster")
    else:
        print("No se pudo conectar. Verificá ES_URL, credenciales y cert.")
        sys.exit(1)

    # ----- 3. Info del cluster -----
    print("\n[3/6] Info del cluster...")
    info = es.info()
    print(f"      Cluster: {info['cluster_name']}")
    print(f"      Versión: {info['version']['number']}")

    # ----- 4. Estructura del índice del workshop -----
    print(f"\n[4/6] Estructura del índice '{ES_INDEX}'...")
    mappings = es.indices.get_mapping(index=ES_INDEX)
    props = mappings[ES_INDEX]["mappings"].get("properties", {})

    print(f"      Campos del índice \"{ES_INDEX}\":")
    print("      " + "-" * 40)
    for campo, config in props.items():
        tipo = config.get("type", "object")
        dims = config.get("dims", "")
        dims_str = f" ({dims} dims)" if dims else ""
        print(f"        {campo:<20} {tipo}{dims_str}")

    count = es.count(index=ES_INDEX)["count"]
    print(f"\n      Documentos indexados: {count}")

    # ----- 5. Documento de ejemplo -----
    print("\n[5/6] Documento de ejemplo...")
    resultado = es.search(index=ES_INDEX, body={"query": {"match_all": {}}, "size": 1})
    doc = resultado["hits"]["hits"][0]
    print(f"      ID: {doc['_id']}")
    for k, v in doc["_source"].items():
        if k == "embedding":
            print(f"        embedding: [{v[0]:.4f}, {v[1]:.4f}, ...] ({len(v)} dims)")
        else:
            val = str(v)[:100] + "..." if len(str(v)) > 100 else str(v)
            print(f"        {k}: {val}")

    # ----- 6. Búsqueda por keyword (BM25) -----
    print("\n[6/6] Búsqueda por keyword (BM25)...")
    query_texto = "error de autenticación"

    resultado = es.search(
        index=ES_INDEX,
        body={
            "query": {"match": {"contenido": {"query": query_texto, "operator": "or"}}},
            "size": 3,
            "_source": ["contenido", "fuente"]
        }
    )

    hits = resultado["hits"]["hits"]
    print(f"      Query: \"{query_texto}\"")
    print(f"      Resultados: {len(hits)}")
    print("      " + "-" * 50)
    for i, hit in enumerate(hits, 1):
        print(f"\n      [{i}] Score: {hit['_score']:.4f}")
        print(f"          Fuente: {hit['_source'].get('fuente', 'N/A')}")
        contenido = hit["_source"].get("contenido", "")[:200]
        print(f"          Contenido: {contenido}...")

    print("\n" + "=" * 60)
    print(" Ejercicio 03 completo")
    print("=" * 60)


if __name__ == "__main__":
    main()
