import sys, os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
load_dotenv()

def get_creds(service):
    keys = {
        "es":     ["ES_URL", "ES_USER", "ES_PASSWORD", "ES_INDEX", "ES_CA_CERT"],
    }
    missing = [k for k in keys[service] if not os.getenv(k) or "TU_" in os.getenv(k, "")]
    if missing:
        print(f"Faltan en .env: {missing}")
        sys.exit(1)
    return {k: os.getenv(k) for k in keys[service]}

def main():
    print("Ejercicio 3: Conexión y primera búsqueda con elasticsearch")

    creds = get_creds("es")

    print("1 Conectando al cluster")

    es = Elasticsearch(
        creds["ES_URL"],
        basic_auth=(creds["ES_USER"], creds["ES_PASSWORD"]),
        ca_certs=creds["ES_CA_CERT"]
    )

    if es.ping():
        print("Conectado al cluster de Elasticsearch")
    else:
        print("No se pudo conectar. Verificá ES_URL, ES_USER y ES_PASSWORD en .env")
        raise SystemExit(1)

    print_cluster = es.info()
    print(f"Cluster: {print_cluster['cluster_name']}")
    print(f"Versión: {print_cluster['version']['number']}")



    print("2 Explorando el índice del workshop")
    index = creds["ES_INDEX"]

    if not es.indices.exists(index=index):
        print(f"El índice '{index}' no existe. Verificar ES_INDEX en .env")
        raise SystemExit(1)

    mappings = es.indices.get_mapping(index=index)
    props = mappings[index]["mappings"].get("properties", {})
    count = es.count(index=index)["count"]

    print(f"\nCampos del índice '{index}':")
    print("-" * 40)
    for campo, config in props.items():
        tipo = config.get("type", "object")
        dims = config.get("dims", "")
        dims_str = f" ({dims} dims)" if dims else ""
        print(f"  {campo:<20} {tipo}{dims_str}")

    print(f"Documentos indexados: {count}")
    assert count > 0, "El índice está vacío"



    print("3 Documento de ejemplo")
    resultado = es.search(
        index=index,
        body={"query": {"match_all": {}}, "size": 1}
    )

    doc = resultado["hits"]["hits"][0]
    print(f"ID: {doc['_id']}")
    for k, v in doc["_source"].items():
        if k == "embedding":
            print(f"  embedding: [{v[0]:.4f}, {v[1]:.4f}, ...] ({len(v)} dims)")
        else:
            val = str(v)[:100] + "..." if len(str(v)) > 100 else str(v)
            print(f"  {k}: {val}")



    print("4. Búsqueda por keyword")
    query_texto = "error de autenticación"
    print(f"Query: '{query_texto}'")

    resultado = es.search(
        index=index,
        body={
            "query": {
                "match": {
                    "contenido": {"query": query_texto, "operator": "or"}
                }
            },
            "size": 3,
            "_source": ["contenido", "fuente"]
        }
    )

    hits = resultado["hits"]["hits"]
    print(f"Resultados: {len(hits)}")
    print("-" * 50)
    for i, hit in enumerate(hits, 1):
        print(f"\n[{i}] Score: {hit['_score']:.4f}")
        print(f"    Fuente: {hit['_source'].get('fuente', 'N/A')}")
        contenido = hit["_source"].get("contenido", "")[:200]
        print(f"    Contenido: {contenido}...")

if __name__ == "__main__":
    main()
