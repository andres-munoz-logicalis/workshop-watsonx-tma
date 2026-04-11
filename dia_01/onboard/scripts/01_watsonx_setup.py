import os
import sys
from dotenv import load_dotenv
load_dotenv()


def get_creds():
    """Carga y valida las credenciales de watsonx.ai desde el .env"""
    keys = ["WX_API_KEY", "WX_PROJECT_ID", "WX_URL"]
    missing = [k for k in keys if not os.getenv(k) or "TU_" in os.getenv(k, "")]
    if missing:
        print(f"Faltan en .env: {missing}")
        print("Corré primero 00_smoke_test.py para validar el entorno")
        sys.exit(1)
    return {k: os.getenv(k) for k in keys}


def main():
    print("Ejercicio 01 — watsonx.ai: Setup y primer llamado")
    print("=" * 55)

    # ========================================================
    # PARTE 1 — OBLIGATORIO
    # ========================================================
    print("\n>>> PARTE 1 — Setup mínimo (obligatorio)\n")

    # ----- Paso 1: cargar credenciales -----
    print("[1/4] Cargando credenciales desde .env...")
    creds = get_creds()
    print(f"      API Key:    {creds['WX_API_KEY'][:8]}...")
    print(f"      Project ID: {creds['WX_PROJECT_ID'][:8]}...")
    print(f"      URL:        {creds['WX_URL']}")

    # ----- Paso 2: inicializar el cliente -----
    print("\n[2/4] Inicializando cliente del SDK...")
    from ibm_watsonx_ai import APIClient, Credentials

    credentials = Credentials(url=creds["WX_URL"], api_key=creds["WX_API_KEY"])
    client = APIClient(credentials)
    print(f"      SDK version: {client.version}")
    # Nota: el SDK maneja automáticamente el refresh del IAM token a partir de la API key.

    # ----- Paso 3: verificar que el proyecto existe y es accesible -----
    print("\n[3/4] Verificando acceso al proyecto...")
    project = client.projects.get_details(creds["WX_PROJECT_ID"])
    nombre = project.get("entity", {}).get("name", "N/A")
    print(f"      Proyecto encontrado: {nombre}")

    # ----- Paso 4: cargar un modelo y hacer un primer llamado -----
    print("\n[4/4] Cargando modelo y haciendo primer llamado...")
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params

    MODEL_ID = "meta-llama/llama-3-3-70b-instruct"

    model = ModelInference(
        model_id=MODEL_ID,
        api_client=client,
        project_id=creds["WX_PROJECT_ID"],
        params={
            Params.MAX_NEW_TOKENS: 100,
            Params.TEMPERATURE: 0.1,
        }
    )

    # Pedimos respuesta corta para evitar truncado por max_tokens
    prompt = "Respondé en máximo 30 palabras: ¿qué hace un modelo de lenguaje grande (LLM)?"
    respuesta = model.generate_text(prompt=prompt)
    print(f"      Modelo: {MODEL_ID}")
    print(f"      Prompt: {prompt}")
    print(f"      Respuesta: {respuesta.strip()}")

    print("\n" + "=" * 55)
    print(" PARTE 1 COMPLETA — Onboarding cumplido")
    print("=" * 55)
    print("\nLos pasos 5 y 6 son opcionales. Podés cerrarlo acá si querés.")
    print("Para correr la Parte 2, dejá que el script siga.\n")

    # ========================================================
    # PARTE 2 — OPCIONAL
    # ========================================================
    print("\n>>> PARTE 2 — Exploración (opcional)\n")

    # ----- Paso 5: ver el detalle del uso de tokens -----
    print("[5/6] Inspeccionando uso de tokens...")
    full = model.generate(prompt=prompt)
    resultado = full["results"][0]
    print(f"      Input tokens:  {resultado['input_token_count']}")
    print(f"      Output tokens: {resultado['generated_token_count']}")
    print(f"      Stop reason:   {resultado['stop_reason']}")
    # Si stop_reason == 'max_tokens', la respuesta se cortó. Si == 'eos_token', terminó natural.

    # ----- Paso 6: cambiar la temperatura y comparar -----
    print("\n[6/6] Comparando temperatura baja vs alta...")
    creative_prompt = "Inventá un nombre para un robot asistente. Solo el nombre."

    for temp in [0.0, 1.0]:
        model_temp = ModelInference(
            model_id=MODEL_ID,
            api_client=client,
            project_id=creds["WX_PROJECT_ID"],
            params={Params.MAX_NEW_TOKENS: 20, Params.TEMPERATURE: temp}
        )
        r = model_temp.generate_text(prompt=creative_prompt).strip()
        print(f"      temp={temp}: {r}")

    print("\n" + "=" * 55)
    print(" PARTE 2 COMPLETA — Listo para Día 2 (Orchestrate)")
    print("=" * 55)


if __name__ == "__main__":
    main()
