import sys, os
from dotenv import load_dotenv
load_dotenv()

from elasticsearch import Elasticsearch

ES_URL      = os.getenv("ES_URL")
ES_USER     = os.getenv("ES_USER", "elastic")
ES_PASSWORD = os.getenv("ES_PASSWORD")
ES_INDEX    = os.getenv("ES_INDEX", "workshop_docs")
ES_CA_CERT  = os.getenv("ES_CA_CERT")

es = Elasticsearch(
    ES_URL,
    basic_auth=(ES_USER, ES_PASSWORD),
    ca_certs=ES_CA_CERT
)

# Crear índice
mapping = {
    "mappings": {
        "properties": {
            "contenido":  {"type": "text"},
            "embedding":  {"type": "dense_vector", "dims": 384},
            "fuente":     {"type": "keyword"},
        }
    }
}

print("Conectando a Elasticsearch...")
print(es.info())

if es.indices.exists(index=ES_INDEX):
    es.indices.delete(index=ES_INDEX)
    print(f"Índice '{ES_INDEX}' eliminado")

es.indices.create(index=ES_INDEX, mappings=mapping["mappings"])
print(f"Índice '{ES_INDEX}' creado")

# Documentos de prueba
docs = [
    {"contenido": "El error de autenticación ocurre cuando el token JWT está expirado o es inválido.", "fuente": "manual_seguridad.pdf"},
    {"contenido": "Para resetear la contraseña el usuario debe ir a /forgot-password e ingresar su email.", "fuente": "manual_usuario.pdf"},
    {"contenido": "El servicio de login falla si el proveedor de identidad externo no responde en 5 segundos.", "fuente": "manual_seguridad.pdf"},
    {"contenido": "Los logs de autenticación se encuentran en /var/log/auth.log en el servidor principal.", "fuente": "guia_ops.pdf"},
    {"contenido": "El deploy en producción requiere aprobación de dos revisores y pasar el pipeline de CI.", "fuente": "guia_deploy.pdf"},
    {"contenido": "Ante una caída del servicio en producción escalar inmediatamente al equipo de guardia.", "fuente": "guia_ops.pdf"},
    {"contenido": "El índice de Elasticsearch se reconstruye automáticamente cada domingo a las 2am.", "fuente": "guia_ops.pdf"},
    {"contenido": "Los errores 500 en el endpoint /api/orders indican un problema con la conexión a la base de datos.", "fuente": "manual_seguridad.pdf"},
    {"contenido": "Para agregar un nuevo modelo al catálogo de watsonx se debe abrir un ticket en el portal IBM.", "fuente": "guia_watsonx.pdf"},
    {"contenido": "El tiempo máximo de respuesta aceptable para la API es de 2 segundos según el SLA vigente.", "fuente": "guia_ops.pdf"},
]

# Vector dummy de 384 dims (en el día 3 estos serán embeddings reales)
vector_dummy = [0.01] * 384

for i, doc in enumerate(docs):
    doc["embedding"] = vector_dummy
    es.index(index=ES_INDEX, id=i+1, body=doc)

print(f"{len(docs)} documentos cargados en '{ES_INDEX}'")
print("Listo para correr 03_elasticsearch.py")
