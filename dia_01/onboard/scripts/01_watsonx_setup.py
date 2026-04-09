import sys, os

from dotenv import load_dotenv
load_dotenv()

def get_creds(service):
    keys = {
        "wx":     ["WX_API_KEY", "WX_PROJECT_ID", "WX_URL"],
    }
    missing = [k for k in keys[service] if not os.getenv(k) or "TU_" in os.getenv(k, "")]
    if missing:
        print(f"Faltan en .env: {missing}")
        sys.exit(1)
    return {k: os.getenv(k) for k in keys[service]}

def main():
    print("Ejercicio 1: Setup y primer llamado a Watsox.AI")

    print("Cargando credenciales desde .env...")
    creds = get_creds("wx")
    print(f"API Key cargada: {creds['WX_API_KEY'][:8]}...")
    print(f"Project ID:      {creds['WX_PROJECT_ID'][:8]}...")
    print(f"URL:             {creds['WX_URL']}")



    print("2 Inicializando cliente")
    from ibm_watsonx_ai import APIClient, Credentials

    credentials = Credentials(url=creds["WX_URL"], api_key=creds["WX_API_KEY"])
    client = APIClient(credentials)
    print(f"SDK version: {client.version}")



    print("3 Verificando proyecto")
    project = client.projects.get_details(creds["WX_PROJECT_ID"])
    nombre = project.get("entity", {}).get("name", "N/A")
    print(f"Proyecto encontrado: {nombre}")



    print("4 Cargando modelo")
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params

    MODEL_ID = "meta-llama/llama-3-3-70b-instruct"

    model = ModelInference(
        model_id=MODEL_ID,
        api_client=client,
        project_id=creds["WX_PROJECT_ID"],
        params={
            Params.MAX_NEW_TOKENS: 200,
            Params.TEMPERATURE: 0.1,
        }
    )
    print(f"Modelo cargado: {MODEL_ID}")



    print("5 Llamado a la API")
    prompt = "En una sola oración, ¿qué hace un modelo de lenguaje grande (LLM)?"
    print(f"Prompt: {prompt}")

    respuesta = model.generate_text(prompt=prompt)
    print(f"\nRespuesta:\n  {respuesta}")

    assert respuesta and len(respuesta) > 10, "La respuesta está vacía"



    print("6 Uso de tokens")
    full = model.generate(prompt=prompt)
    resultado = full["results"][0]
    print(f"Input tokens:  {resultado['input_token_count']}")
    print(f"Output tokens: {resultado['generated_token_count']}")
    print(f"Stop reason:   {resultado['stop_reason']}")

if __name__ == "__main__":
    main()
