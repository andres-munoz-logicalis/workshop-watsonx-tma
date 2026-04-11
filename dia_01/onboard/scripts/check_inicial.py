"""
Si todos los checks salen [OK], estás listo para el ejercicio 00.
"""

import os
import sys
import socket
from urllib import request, error

OK_TAG    = "[OK]   "
FALTA_TAG = "[FALTA]"
INFO_TAG  = "[--]   "

def check(label, ok, ok_detail="", fail_detail=""):
    if ok:
        line = f"  {OK_TAG} {label}"
        if ok_detail:
            line += f" — {ok_detail}"
    else:
        line = f"  {FALTA_TAG} {label}"
        if fail_detail:
            line += f" — {fail_detail}"
    print(line)
    return ok

def info(label, present):
    tag = OK_TAG if present else INFO_TAG
    print(f"  {tag} {label}")
    return present

def section(title):
    print(f"\n{title}")
    print("-" * 50)

def main():
    print("=" * 50)
    print(" Check inicial — Workshop Watsonx")
    print("=" * 50)

    all_ok = True

    # 1. Python y librerías
    section("1. Entorno Python")
    all_ok = check(
        f"Python {sys.version_info.major}.{sys.version_info.minor}",
        sys.version_info >= (3, 9),
        fail_detail="se requiere Python 3.9+"
    ) and all_ok

    libs = ["dotenv", "ibm_watsonx_ai", "elasticsearch"]
    for lib in libs:
        try:
            __import__(lib)
            all_ok = check(f"import {lib}", True) and all_ok
        except ImportError as e:
            all_ok = check(f"import {lib}", False, fail_detail=str(e)) and all_ok

    # 2. Archivo .env
    section("2. Archivo .env")
    from dotenv import load_dotenv
    env_loaded = load_dotenv()
    all_ok = check(
        ".env encontrado y cargado",
        env_loaded,
        fail_detail="ejecutá `cp example.txt .env` y completá los valores"
    ) and all_ok

    # 3. Variables de watsonx.ai (obligatorias para el onboarding)
    section("3. Variables watsonx.ai (obligatorias)")
    wx_vars = ["WX_API_KEY", "WX_PROJECT_ID", "WX_URL"]
    for var in wx_vars:
        val = os.getenv(var, "")
        present = bool(val) and "TU_" not in val
        preview = f"{val[:8]}..." if present and len(val) > 8 else val
        all_ok = check(
            var, present,
            ok_detail=preview,
            fail_detail="vacío o placeholder"
        ) and all_ok

    # 4. Variables de Elasticsearch (opcionales en onboarding, necesarias en Día 3)
    section("4. Variables Elasticsearch (opcional, Día 3)")
    es_vars = ["ES_URL", "ES_USER", "ES_PASSWORD", "ES_INDEX", "ES_CA_CERT"]
    for var in es_vars:
        val = os.getenv(var, "")
        present = bool(val) and "TU_" not in val
        info(var, present)
 
    # Verificar que el cert exista solo si está configurado (no bloqueante)
    ca_cert = os.getenv("ES_CA_CERT", "")
    if ca_cert:
        cert_exists = os.path.isfile(ca_cert)
        info(f"archivo de cert en {ca_cert}", cert_exists)
        if not cert_exists:
            print(f"(no bloqueante hoy, pero lo vas a necesitar en el Día 3)")
 
    # 5. Conectividad de red a IBM Cloud
    section("5. Conectividad a IBM Cloud")
    try:
        socket.gethostbyname("iam.cloud.ibm.com")
        all_ok = check("DNS resuelve iam.cloud.ibm.com", True) and all_ok
    except socket.gaierror as e:
        all_ok = check("DNS resuelve iam.cloud.ibm.com", False, fail_detail=str(e)) and all_ok
 
    try:
        req = request.Request("https://iam.cloud.ibm.com/identity/.well-known/openid-configuration")
        with request.urlopen(req, timeout=5) as resp:
            all_ok = check(
                "HTTPS a iam.cloud.ibm.com",
                resp.status == 200,
                ok_detail=f"status {resp.status}",
                fail_detail=f"status inesperado {resp.status}"
            ) and all_ok
    except (error.URLError, TimeoutError) as e:
        all_ok = check(
            "HTTPS a iam.cloud.ibm.com",
            False,
            fail_detail=f"problema de red o proxy: {e}"
        ) and all_ok

    # Resultado final
    print("\n" + "=" * 50)
    if all_ok:
        print(" Todo OK. Podés avanzar al ejercicio 00.")
    else:
        print(" Hay items que resolver. Revisá los [FALTA] y [ERROR] arriba.")
        print(" Lo más común: completar el .env o instalar dependencias.")
    print("=" * 50)
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
