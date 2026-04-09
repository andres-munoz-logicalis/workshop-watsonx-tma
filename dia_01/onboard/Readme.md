# Workshop Watsonx — Entorno de trabajo

## Credenciales

```bash
cp .env.example .env
```

En `.env` y reeplazar valores:

---

## Setup inicial

Constuir entorno
```bash
docker compose build
```
---

## Uso

```bash
# Levantar el entorno
docker compose up -d

# Jupyter disponible en:
# http://localhost:8888/?token=workshop
```
Para detenerlo:

```bash
docker compose down
```
---
## Ejecucion - Opcion 1: Notebooks

- Ingresar a http://localhost:8888/?token=workshop 
- Acceder a la carpeta notebooks
- En la UI de jupyter correr cada script

---
## Ejecucion - Opcion 2: Scripts
### Correr los scripts desde la terminal del contenedor

```bash
# Abrir una terminal dentro del contenedor
docker compose exec workshop bash

# Desde adentro del contenedor
cd scripts
python 01_watsonx_setup.py
python 02_sdk_prompts.py
python 03_elasticsearch.py
python 04_milvus.py
```

### O directamente sin entrar al contenedor:

```bash
docker compose exec workshop python scripts/01_watsonx_setup.py
```

---

## Troubleshooting

**El puerto 8888 ya está en uso:**
```bash
# Cambiar el puerto en docker-compose.yml
ports:
  - "8889:8888"
# Luego acceder a localhost:8889/?token=workshop
```

**Error de credenciales en el script:**
- Verificar que el `.env` tenga los valores correctos
- Verificar que no haya espacios alrededor del `=`

**El build falla:**
- Verificar que Docker Desktop esté corriendo
- Intentar con `docker compose build --no-cache`
