# Workshop Watsonx — Entorno y ejercicios

Este repo contiene el entorno Docker y los ejercicios de onboarding del workshop de Watsonx. Está pensado para correr todo localmente con un solo comando, sin instalar nada en tu máquina más allá de Docker.

---

## Qué vas a encontrar acá

```
.
├── docker-compose.yml          # Levanta el contenedor con Jupyter
├── Dockerfile                  # Imagen con Python + dependencias
├── requirements.txt            # Librerías Python
├── example.txt                 # Template del .env (copialo a .env)
├── certs/
│   └── ca.crt                  # Certificado del cluster Elasticsearch
├── notebooks/                  # Ejercicios en formato Jupyter
│   ├── check_inicial.ipynb
│   ├── 00_llm_conceptos.ipynb
|   ├── 01_watsonx_ai.ipynb
│   ├── 02_sdk_prompts.ipynb
│   └── 03_elasticsearch.ipynb
└── scripts/                    # Mismos ejercicios en formato .py (exceptuando 00_llm_conceptos)
    ├── check_inicial.py
    ├── 01_watsonx_setup.py
    ├── 02_sdk_prompts.py
    └── 03_elasticsearch.py
```

---

## Setup inicial 
### 1. Cloná el repo (sino lo tenes ya) y entrá a la carpeta onboard del dia 01

```bash
git clone <repo-url>
```

### 2. Configurá las credenciales

```bash
cp example.txt .env
```

Abrí `.env` con tu editor y completá los valores. Las credenciales de watsonx.ai te las da el tutor o las generás vos desde IBM Cloud (ver sección "Obtener credenciales" más abajo).

```bash
# watsonx.ai
WX_API_KEY=tu_api_key_aca
WX_PROJECT_ID=tu_project_id_aca
WX_URL=https://us-south.ml.cloud.ibm.com

# Elasticsearch
ES_URL=https://...
ES_USER=elastic
ES_PASSWORD=...
ES_INDEX=workshop_docs
ES_CA_CERT=certs/ca.crt
```

**No subas el `.env` a git.** Está en `.gitignore` por algo.

### 3. Construí y levantá el entorno

```bash
docker compose build
docker compose up -d
```

Cuando termine, Jupyter va a estar disponible en:

**http://localhost:8888/?token=workshop**

Para apagar todo cuando termines:

```bash
docker compose down
```

---

## Cómo correr los ejercicios

Tenés **dos opciones** según con qué te sientas más cómodo. Los notebooks y los scripts hacen lo mismo, elegí uno.

### Opción A — Notebooks (recomendado)

1. Abrí **http://localhost:8888/?token=workshop**
2. Entrá a la carpeta `notebooks/`
3. Corré los ejercicios en orden: `00 → 01 → (02) → (03)`

### Opción B — Scripts desde terminal

```bash
# Entrar al contenedor
docker compose exec workshop bash

# Adentro del contenedor
cd scripts
python check_inicial.py
python 01_watsonx_setup.py
```

O directo sin entrar al contenedor:

```bash
docker compose exec workshop python scripts/check_inicial.py
```

---

## Orden recomendado de los ejercicios

| # | Ejercicio | Tiempo | Cuándo |
|---|---|---|---|
| **Inicio** | `check_inicial` | ~1 min | **Antes que cualquier otra cosa.** Valida que el entorno está OK. |
| **00** | `00_llm_conceptos` | ~5 min | **Repaso de teoria gracias a ejercicios**|
| **01** | `01_watsonx_setup` (Parte 1) | ~5 min | **Onboarding** |
| 01 | `01_watsonx_setup` (Parte 2) | ~5 min | Opcional - Exploración de tokens y temperatura. |
| 02 | `02_sdk_prompts` | ~10 min | Opcional - Chat, JSON output, few-shot. |
| 03 | `03_elasticsearch` | ~10 min | Opcional - Preview Elastic conexión y primera búsqueda. |

**Para el bloque de onboarding del workshop solo necesitás llegar al final de la Parte 1 del ejercicio 01.** El resto está como material de práctica para los que terminen rápido o quieran profundizar después.

---

## Obtener credenciales de watsonx.ai

Si el tutor no te las dio precargadas:

1. Entrá a [cloud.ibm.com](https://cloud.ibm.com) con tu cuenta
2. Navegá al **Resource Group** del workshop → instancia de **watsonx.ai**
3. Abrí la instancia, andá a **Manage → Access (IAM) → API keys**
4. Crear API key. **Copiala y guardala** — no se puede ver de nuevo.
5. El `WX_PROJECT_ID` lo encontrás en watsonx.ai → tu proyecto → **Manage → General**
6. Pegá ambos valores en tu `.env`

---

## Troubleshooting

### Problemas con Docker

**El puerto 8888 ya está en uso:**
```yaml
# Editá docker-compose.yml y cambiá el puerto del host
ports:
  - "8889:8888"
# Después accedé a http://localhost:8889/?token=workshop
```

**El build falla:**
```bash
docker compose build --no-cache
```
Verificá también que Docker Desktop esté corriendo.

**Jupyter no abre:**
```bash
# Ver los logs del contenedor
docker compose logs workshop
```

### Problemas con credenciales

| Error | Causa | Solución |
|---|---|---|
| `Faltan en .env: [...]` | El `.env` no está completo | Revisá que cada variable tenga un valor real, no `TU_...` |
| `401 Unauthorized` | API key vencida o mal copiada | Regenerá la key en IBM Cloud, copiala sin espacios |
| `403 Forbidden` | La key no tiene permisos sobre el proyecto | Pedile al facilitador acceso al resource group |
| `404 project not found` | `WX_PROJECT_ID` incorrecto o región distinta | Verificá el ID y que `WX_URL` apunte a la región correcta |

### Problemas con el .env

- **Verificá que no haya espacios alrededor del `=`**: `WX_API_KEY=abc` ✅, `WX_API_KEY = abc` ❌
- **No uses comillas** salvo que el valor las requiera: `WX_URL=https://...` ✅
- **Si editaste el `.env`** mientras el contenedor estaba corriendo, reiniciá: `docker compose restart workshop`

### Problemas con Elasticsearch

**`No se pudo conectar`:**
- Verificá que `ES_CA_CERT` apunte a un archivo que exista (debería estar en `certs/ca.crt`)
- Verificá que `ES_URL` esté completo (con `https://` y puerto si aplica)
- El cert se monta en el contenedor desde la carpeta `certs/` del repo. Si no lo ves adentro del contenedor, revisá el volume mount en `docker-compose.yml`.

---

Los ejercicios `02_sdk_prompts` quedan como **material de práctica libre** para cualquier momento.

---

## Recursos adicionales

- Guía teórica del workshop: `contenido_teorico.md` (en este mismo repo)
- Documentación oficial de watsonx.ai: [ibm.com/docs/watsonx](https://www.ibm.com/docs/en/watsonx)
- Documentación de Orchestrate: [cloud.ibm.com/docs/watsonx-orchestrate](https://cloud.ibm.com/docs/watsonx-orchestrate)
