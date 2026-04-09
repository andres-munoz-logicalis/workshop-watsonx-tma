"""
utils.py — Helpers compartidos por todos los scripts del workshop.
Carga credenciales desde .env y provee output formateado.
"""
import os
from dotenv import load_dotenv

load_dotenv()

def checkpoint(numero, descripcion):
    print(f"CHECKPOINT {numero} completado {descripcion}")
    print(RESET)

def get_wx_credentials():
    creds = {
        "api_key":    os.getenv("WX_API_KEY"),
        "project_id": os.getenv("WX_PROJECT_ID"),
        "url":        os.getenv("WX_URL", "https://us-south.ml.cloud.ibm.com"),
    }
    missing = [k for k, v in creds.items() if not v or "TU_" in str(v)]
    if missing:
        fail(f"Faltan variables en .env: {missing}")
        raise SystemExit(1)
    return creds

def get_es_credentials():
    creds = {
        "url":      os.getenv("ES_URL"),
        "user":     os.getenv("ES_USER", "elastic"),
        "password": os.getenv("ES_PASSWORD"),
        "index":    os.getenv("ES_INDEX", "workshop_docs"),
    }
    missing = [k for k, v in creds.items() if not v or "TU_" in str(v)]
    if missing:
        fail(f"Faltan variables en .env: {missing}")
        raise SystemExit(1)
    return creds

def get_milvus_credentials():
    creds = {
        "uri":        os.getenv("MILVUS_URI"),
        "token":      os.getenv("MILVUS_TOKEN"),
        "collection": os.getenv("MILVUS_COLLECTION", "workshop_documentos"),
    }
    missing = [k for k, v in creds.items() if not v or "TU_" in str(v)]
    if missing:
        fail(f"Faltan variables en .env: {missing}")
        raise SystemExit(1)
    return creds
