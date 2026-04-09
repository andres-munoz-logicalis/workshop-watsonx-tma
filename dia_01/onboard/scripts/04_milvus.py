import random
import sys, os

from dotenv import load_dotenv
load_dotenv()

DIMS = 384  # dimensiones del modelo de embedding del workshop

def get_creds(service):
    keys = {
        "ml": ["MILVUS_URI", "MILVUS_TOKEN", "MILVUS_COLLECTION"],
    }
    missing = [k for k in keys[service] if not os.getenv(k) or "TU_" in os.getenv(k, "")]
    if missing:
        print(f" Faltan en .env: {missing}")
        sys.exit(1)
    return {k: os.getenv(k) for k in keys[service]}

def main():
    header("Ejercicio 4: Milvus - watsonx.data: Conexión y schema")

    creds = get_creds("ml")


    header("1 Conectando a Milvus")
    from pymilvus import connections, utility, Collection

    connections.connect(
        alias="default",
        uri=creds["MILVUS_URI"],
        token=creds["MILVUS_TOKEN"]
    )
    ok("Conectado a Milvus")



    header("2 Colecciones disponibles")
    colecciones = utility.list_collections()

    if not colecciones:
        fail("No hay colecciones disponibles. Verificá el token y el URI.")
        raise SystemExit(1)

    for c in colecciones:
        marker = "  <- workshop" if c == creds["MILVUS_COLLECTION"] else ""
        print(f" {c}{marker}")

    assert creds["collection"] in colecciones, \
        f"La colección '{creds['MILVUS_COLLECTION']}' no existe. Revisar MILVUS_COLLECTION en .env"
    ok(f"Colección del workshop encontrada: {creds['MILVUS_COLLECTION']}")



    header("3 Schema de la colección")
    col = Collection(creds["MILVUS_COLLECTION"])
    col.load()

    schema = col.schema
    info(f"Descripción: {schema.description}")
    print("\nCampos:")
    print("-" * 50)
    for field in schema.fields:
        es_pk   = " (primary key)" if field.is_primary else ""
        dims    = field.params.get("dim", "")
        dims_str = f" [{dims} dims]" if dims else ""
        print(f"  {field.name:<20} {field.dtype.name}{dims_str}{es_pk}")

    ok(f"Entidades almacenadas: {col.num_entities}")
    assert col.num_entities > 0, "La colección está vacía"



    header("4 Búsqueda vectorial de prueba")
    warn("Vector aleatorio — los resultados no serán semánticamente relevantes.")
    warn("En el Día 3 usaremos embeddings reales generados desde el query del usuario.")

    query_vector = [random.uniform(-1, 1) for _ in range(DIMS)]

    resultados = col.search(
        data=[query_vector],
        anns_field="embedding",
        param={"metric_type": "COSINE", "ef": 64},
        limit=3,
        output_fields=["contenido", "fuente"]
    )

    print(f"\nResultados (top 3):")
    print("-" * 50)
    for i, hit in enumerate(resultados[0], 1):
        print(f"\n[{i}] Distancia: {hit.distance:.4f}")
        print(f"    Fuente: {hit.entity.get('fuente', 'N/A')}")
        contenido = hit.entity.get("contenido", "")[:150]
        print(f"    Contenido: {contenido}...")

if __name__ == "__main__":
    main()
