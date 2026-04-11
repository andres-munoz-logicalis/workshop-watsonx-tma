import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from pypdf import PdfReader

load_dotenv()

ES_URL      = os.getenv("ES_URL")
ES_USER     = os.getenv("ES_USER", "elastic")
ES_PASSWORD = os.getenv("ES_PASSWORD")
ES_INDEX    = os.getenv("ES_INDEX_PDF", "workshop_pdfs")
ES_CA_CERT  = os.getenv("ES_CA_CERT")

ELSER_MODEL_ID = ".elser_model_2_linux-x86_64"
PIPELINE_ID    = f"{ES_INDEX}-elser-pipeline"

DOCS_DIR = Path(__file__).parent / "docs"

es = Elasticsearch(
    ES_URL,
    basic_auth=(ES_USER, ES_PASSWORD),
    ca_certs=ES_CA_CERT,
)

print("Conectando a Elasticsearch...")
print(es.info())


# Validar que ELSER esté desplegado y andando

print(f"\nVerificando deployment de {ELSER_MODEL_ID}...")
try:
    stats = es.ml.get_trained_models_stats(model_id=ELSER_MODEL_ID)
    deployment_stats = stats["trained_model_stats"][0].get("deployment_stats")
    if not deployment_stats or deployment_stats.get("state") != "started":
        print(f"ERROR: {ELSER_MODEL_ID} no está en estado 'started'.")
        print("       Desplegalo desde Kibana -> ML -> Trained Models.")
        sys.exit(1)
    print(f"OK: {ELSER_MODEL_ID} está started.")
except Exception as e:
    print(f"ERROR verificando ELSER: {e}")
    sys.exit(1)

# Crear ingest pipeline
pipeline_body = {
    "description": "Genera embeddings ELSER sobre el campo 'contenido'",
    "processors": [
        {
            "inference": {
                "model_id": ELSER_MODEL_ID,
                "input_output": [
                    {
                        "input_field": "contenido",
                        "output_field": "contenido_embedding",
                    }
                ],
            }
        }
    ],
}

print(f"\nCreando/actualizando ingest pipeline '{PIPELINE_ID}'...")
es.ingest.put_pipeline(id=PIPELINE_ID, body=pipeline_body)
print(f"Pipeline '{PIPELINE_ID}' listo.")

# Crear índice 
mapping = {
    "mappings": {
        "properties": {
            "contenido":           {"type": "text"},
            "contenido_embedding": {"type": "sparse_vector"},
            "fuente":              {"type": "keyword"},
            "pagina":              {"type": "integer"},
        }
    },
    "settings": {
        "index": {
            "default_pipeline": PIPELINE_ID
        }
    }
}

if es.indices.exists(index=ES_INDEX):
    es.indices.delete(index=ES_INDEX)
    print(f"\nÍndice '{ES_INDEX}' eliminado")

es.indices.create(
    index=ES_INDEX,
    mappings=mapping["mappings"],
    settings=mapping["settings"],
)
print(f"Índice '{ES_INDEX}' creado (pipeline default: {PIPELINE_ID})")

# Leer PDFs de docs/ y extraer texto página por página
if not DOCS_DIR.exists():
    print(f"\nERROR: no existe la carpeta {DOCS_DIR}")
    print("       Creá la carpeta 'docs/' y poné los PDFs adentro.")
    sys.exit(1)

pdf_files = sorted(DOCS_DIR.glob("*.pdf"))
if not pdf_files:
    print(f"\nERROR: no se encontraron PDFs en {DOCS_DIR}")
    sys.exit(1)

print(f"\nEncontrados {len(pdf_files)} PDFs en {DOCS_DIR}")

# Indexar cada página como un documento (una página = un chunk.)
total_docs = 0
doc_id = 1

for pdf_path in pdf_files:
    print(f"\nProcesando {pdf_path.name}...")
    try:
        reader = PdfReader(str(pdf_path))
    except Exception as e:
        print(f"  No se pudo abrir el PDF: {e}")
        continue

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            text = (page.extract_text() or "").strip()
        except Exception as e:
            print(f"  Página {page_num}: error extrayendo texto ({e})")
            continue

        if not text:
            continue

        doc = {
            "contenido": text,
            "fuente": pdf_path.name,
            "pagina": page_num,
        }

        es.index(index=ES_INDEX, id=doc_id, document=doc)
        doc_id += 1
        total_docs += 1

    print(f"  {pdf_path.name}: indexadas {page_num} páginas")

# Forzar refresh para que queden visibles de inmediato
es.indices.refresh(index=ES_INDEX)

print(f"\n{total_docs} documentos (páginas) cargados en '{ES_INDEX}'")
print(f"Modelo de embeddings: {ELSER_MODEL_ID}")
