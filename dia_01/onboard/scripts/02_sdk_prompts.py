import json
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
    print("Ejercicio 2: SDK, chat, prompts y output estructurado")

    creds = get_creds("wx")
    from ibm_watsonx_ai import APIClient, Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params

    client = APIClient(Credentials(url=creds["WX_URL"], api_key=creds["WX_API_KEY"]))
    model = ModelInference(
        model_id="meta-llama/llama-3-3-70b-instruct",
        api_client=client,
        project_id=creds["WX_PROJECT_ID"]
    )

    print("Cliente listo")


    print("1 Chat con system prompt")

    messages = [
        {
            "role": "system",
            "content": (
                "Sos un asistente técnico experto en watsonx. "
                "Respondés de forma concisa y siempre en español."
            )
        },
        {
            "role": "user",
            "content": "¿Cuál es la diferencia entre un modelo instruct y un modelo chat?"
        }
    ]

    response = model.chat(messages=messages, params={Params.MAX_NEW_TOKENS: 200})
    respuesta = response["choices"][0]["message"]["content"]
    print("Pregunta: ¿Diferencia entre modelo instruct y chat?")
    print(f"\nRespuesta:\n{respuesta}\n")



    print("2 Output estructurado en JSON")

    messages_json = [
        {
            "role": "system",
            "content": (
                "Te dedicas a clasificar tickets de soporte técnico.\n"
                "SIEMPRE respondes con un JSON válido con este esquema:\n"
                '{"categoria": str, "prioridad": "baja|media|alta|critica", "resumen": str}\n'
                "No incluyas texto fuera del JSON."
            )
        },
        {
            "role": "user",
            "content": "La app de producción no levanta después del deploy de las 14hs."
        }
    ]

    response = model.chat(messages=messages_json, params={Params.MAX_NEW_TOKENS: 300})
    raw = response["choices"][0]["message"]["content"]
    print(f"Raw response: {raw}")

    try:
        parsed = json.loads(raw)
        assert "categoria" in parsed
        assert parsed["prioridad"] in ["baja", "media", "alta", "critica"]
        assert "resumen" in parsed
        print("\nJSON parseado correctamente:")
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
        print("Schema válido")
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"El modelo no devolvió JSON válido: {e}")
        print("Probá bajar la temperatura a 0.0 en el model params")
        raise SystemExit(1)



    print("3 Few-shot — ejemplos en el system prompt")

    messages_fewshot = [
        {
            "role": "system",
            "content": (
                "Clasificás incidentes según estos ejemplos:\n\n"
                'Input: "La app no carga"\n'
                'Output: {"categoria": "UI", "prioridad": "media"}\n\n'
                'Input: "Perdimos datos de producción"\n'
                'Output: {"categoria": "DATA", "prioridad": "critica"}\n\n'
                'Input: "El login tarda 30 segundos"\n'
                'Output: {"categoria": "PERFORMANCE", "prioridad": "alta"}\n\n'
                "Respondé SOLO con el JSON."
            )
        },
        {
            "role": "user",
            "content": "El login falla para usuarios con caracteres especiales en el mail."
        }
    ]

    response = model.chat(messages=messages_fewshot, params={Params.MAX_NEW_TOKENS: 300})
    raw = response["choices"][0]["message"]["content"]
    print(f"Clasificación few-shot: {raw}")

    try:
        parsed = json.loads(raw)
        print(f"categoria={parsed.get('categoria')}  prioridad={parsed.get('prioridad')}")
    except json.JSONDecodeError:
        print("Respuesta no es JSON puro, revisar system prompt")

if __name__ == "__main__":
    main()
