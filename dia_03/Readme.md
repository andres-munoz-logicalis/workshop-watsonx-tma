# Hands-on Día 3 — Base de conocimientos con Elasticsearch + Orchestrate

**Duración estimada:** 30-45 min (con extras opcionales).

**Objetivo:** poblar un índice de Elasticsearch con contenido web, explorar un índice pre-cargado con papers de IA, y construir un agente RAG en watsonx Orchestrate que responda preguntas citando esas fuentes.

**Qué vas a tener al final:**
- Un índice propio en Elasticsearch poblado con el crawler de Enterprise Search.
- Familiaridad con la vista de Kibana para explorar documentos indexados con embeddings ELSER.
- Una Knowledge Base en Orchestrate conectada a un índice de Elasticsearch.
- Un agente de Orchestrate que responde preguntas usando esa KB.

---

## Pre-requisitos (ya resueltos)

> Informativo. No hace falta que lo ejecutes.

- Cluster de Elasticsearch **Platinum** con Kibana y Enterprise Search accesibles.
- Modelo **`.elser_model_2_linux-x86_64`** descargado y **started** en ML → Trained Models.
- Índice pre-poblado **`kb-ai-docs`** con papers de IA ya chunkeados y embebidos con ELSER.
- Proyecto de watsonx Orchestrate con permisos para crear Knowledge Bases y agentes.

---

# Ejercicios principales

## Ejercicio 1 — Crear un web crawler y poblar un índice propio

**Objetivo:** ver en vivo cómo se ingiere contenido a Elasticsearch con el crawler de Enterprise Search, aplicando embeddings ELSER automáticamente vía ingest pipeline.

1. En Kibana, andá a **Search → Content → Indices → Create a new index**.
2. Elegí **Use a web crawler**.
3. Nombre del índice: `kb-<nombre-grupo>-crawler`. Tiene que ser único para no pisar al resto.
4. Confirmá la creación.
5. En la pestaña **Manage Domains**, agregá **uno** de estos dominios:
   - `https://www.ibm.com/think/topics/artificial-intelligence` (recomendado)
   - `https://research.ibm.com/blog`
   - Cualquier otro sitio público.
6. **Validá el dominio** cuando Kibana te lo pida.
7. En **Crawl rules** podés opcionalmente limitar por path. Para este ejercicio dejá el default.
8. **Antes de lanzar el crawl**, andá a **Pipelines → Copy and customize** y activá **ML inference pipeline** con:
   - **Model:** `.elser_model_2_linux-x86_64`
   - **Source field:** `body`
   - **Target field:** `body_embedding`
9. Volvé a **Overview** y hacé click en **Crawl → Crawl all domains on this index**.
10. Esperá 1-3 minutos. Refrescá **Documents** hasta ver al menos 15-20 docs con `body_embedding` poblado.

### Revision

- [ ] Tu índice tiene al menos 15 documentos.
- [ ] Los docs tienen `body_embedding` con lista de tokens y pesos (sparse vector de ELSER).
- [ ] Anotaste: nombre del índice, campo de texto (`body`), campo de embedding (`body_embedding`).

> **Si el crawl no arranca:** cambiá de dominio. Algunos sitios bloquean bots. `research.ibm.com/blog` suele andar bien.

---

## Ejercicio 2 — Revisar el índice pre-cargado de PDFs

**Objetivo:** explorar en Kibana un índice ya poblado con papers de arXiv sobre IA para entender cómo se ve la data indexada con ELSER antes de consumirla desde Orchestrate.

Arquitectura simple (actual):
PDF
 ↓
pypdf (page-based)
 ↓
ELSER ingest pipeline
 ↓
Elasticsearch (sparse_vector)
 ↓
query simple
 ↓
IBM Orchestrate agent

Este índice se llama **`kb-ai-docs`** y ya está listo corriendo un script Python que extrae texto de los PDFs, los parte en páginas y los indexa a través de un ingest pipeline con ELSER. Si te interesa ver cómo, está el Extra 1 al final. Los pdf se extrajero de [arxiv](https://arxiv.org/list/cs.AI/recent)

1. En Kibana, andá a **Search → Content → Indices**.
2. Entrá a **`kb-ai-docs`**.
3. En **Overview**, mirá el **Document count**.
4. Andá a **Mappings** y observá los campos:
   - `contenido` — texto extraído de cada página (`type: text`)
   - `contenido_embedding` — sparse vector generado por ELSER (`type: sparse_vector`)
   - `fuente` — nombre del PDF (`type: keyword`)
   - `pagina` — número de página dentro del PDF (`type: integer`)
5. Andá a **Documents** y hacé click en cualquier doc. Expandí el JSON y prestá atención a `contenido_embedding`: vas a ver un objeto con decenas de pares `"token": peso`. Eso es lo que ELSER genera — no es un vector denso de floats, son tokens expandidos con peso de importancia. Por eso se llama *sparse*.
6. Buscá en la barra de **Documents** algún término (ej: `transformer`, `reinforcement`). Esta búsqueda es léxica, sirve solo para explorar.

### Revision

- [ ] Entendiste qué hay en `kb-ai-docs`: páginas de PDFs + embeddings ELSER.
- [ ] Viste cómo se ve un sparse vector en un documento real.
- [ ] Anotaste: índice (`kb-ai-docs`), campo texto (`contenido`), campo embedding (`contenido_embedding`).

---

## Ejercicio 3 — Agente RAG en watsonx Orchestrate

El paso central: conectar un índice de Elasticsearch a Orchestrate como KB y crear un agente que lo use.

> Podés conectar el índice del Ejercicio 1 o el `kb-ai-docs`. Si te alcanza el tiempo, hacé los dos como dos agentes separados.

### 3.1 Crear la Knowledge Base

1. Orchestrate → menú lateral → **Build** → **All knowledge** → **Create knowledge**.
2. Tipo: `Elasticsearch`.
3. Completá la conexión:
   - **Endpoint / URL:** el de la db.
   - **Puerto:** el de la db
   - **Autenticación:** API key (si sabes crearla) o Basic usando usuario y password provista.
4. - **Title:** `kb-ai-docs` o `kb-<grupo>-crawler`.
   - **Body:** `contenido` para el que haga referencia a los pdf y `body` para los crawler.
3. **Descripción:** una línea enfocada en qué preguntas puede responder (el agente la lee para decidir cuándo consultarla).
   - Para `kb-ai-docs`: *"Papers recientes de arXiv sobre inteligencia artificial, machine learning y deep learning"*.
   - Para tu crawler: *"Artículos de IBM sobre inteligencia artificial y tecnologías relacionadas"*.
6. Guardá y esperá el check verde.

### 3.2 Crear el agente

1. Orchestrate → **Agents → Create agent**.
2. Nombre: `knowledge-assistant-<grupo>`.
3. Descripción: una línea sobre qué preguntas responde.
4. **Knowledge:** asociá la KB que creaste.
5. **Tools:** ninguna por ahora.
6. **Instructions (system prompt):** copiá el prompt de la sección 3.3.
7. Guardá.

### 3.3 System prompt del agente

```
Sos un asistente experto que responde preguntas usando EXCLUSIVAMENTE la
información disponible en tu base de conocimiento conectada.

REGLAS DE RESPUESTA:
1. Antes de responder cualquier pregunta, consultá siempre tu base de
   conocimiento. No respondas de memoria.
2. Basá tu respuesta únicamente en los fragmentos recuperados. No inventes
   datos, cifras, nombres ni fechas que no estén en el contexto.
3. Si la base de conocimiento no contiene información suficiente para
   responder, decilo explícitamente con esta frase:
   "No encontré información sobre eso en la base de conocimiento."
   No intentes responder con conocimiento general.
4. Citá siempre las fuentes al final de la respuesta, indicando el título,
   nombre de archivo o URL del documento del que sacaste cada dato. Formato:
   Fuentes:
   - [título, archivo o URL 1]
   - [título, archivo o URL 2]
5. Si la pregunta es ambigua, pedí una aclaración antes de buscar.
6. Respondé en el mismo idioma en que te pregunten (español o inglés).

ESTILO:
- Respuestas concisas y directas. Preferí 3-5 oraciones sobre párrafos
  largos, salvo que la pregunta pida detalle.
- Usá viñetas solo cuando enumeres elementos comparables.
- No uses frases de relleno tipo "excelente pregunta" o "según mi base de
  conocimiento". Andá directo a la respuesta.

QUÉ NO HACER:
- No inventes URLs ni referencias que no estén en los fragmentos recuperados.
- No respondas preguntas fuera del dominio de tu base de conocimiento
  (por ejemplo, temas personales, matemática general, código). Redirigí
  amablemente con: "Solo puedo responder preguntas sobre [tema de la KB]."
```

### 3.4 Probar el agente

Desde el chat de Orchestrate, hacé al menos 4 preguntas y anotá los resultados:

1. **Pregunta directa** con palabras exactas de los documentos.
2. **Pregunta semántica**: mismo concepto, palabras distintas. Acá ELSER se luce.
3. **Pregunta sobre algo que NO está** en la base. El agente debe responder con la frase de fallback, no inventar.
4. **Pregunta fuera de dominio** (ej: "¿cuál es la capital de Francia?"). Debe redirigir.

### Revision

- [ ] El agente cita fuentes reales del índice.
- [ ] Cuando preguntás algo que no está, responde con la frase de fallback en lugar de inventar.
- [ ] Cuando preguntás fuera de dominio, redirige.

---

# Ejercicios extra (opcionales)

Para quienes terminen antes. Se pueden hacer durante el almuerzo o la tarde.

## Extra 1 — Indexar tus propios PDFs con Python

Mirar el script que usó el instructor para poblar `kb-ai-docs` y crear tu propio índice.

1. En el repo, andá a `dia_00/python_setup/01_populate_pdf_elastic.py`.
2. Revisá el código: vas a ver cómo
   - valida que ELSER esté `started`,
   - crea un **ingest pipeline** con el `inference processor` apuntando a ELSER,
   - crea el índice con `sparse_vector` para el embedding y el pipeline como `default_pipeline`,
   - extrae texto página por página con `pypdf`,
   - indexa cada página como un documento independiente.
3. Para crear tu propio índice:
   - Descargá 2-3 PDFs que te interesen.
   - Ponelos en una carpeta `docs/` al lado del script.
   - Cambiá `ES_INDEX_PDF` en el `.env` a un nombre único como `kb-<grupo>-pdfs`.
   - Corré: `python 01_populate_pdf_elastic.py`.
4. Verificá en Kibana que tu nuevo índice tenga los docs.
5. Conectalo a Orchestrate como una segunda KB y armá un segundo agente. Ahora tenés dos agentes sobre dos dominios distintos — perfecto para experimentar con orquestación.

## Extra 2 - Modificar el prompt

Modifica y personaliza los promts (se recomienda hacerlos en ingles), agrega reglas de presentacion e intenta mejorar las reglas que se imponen.

# Extra 3 - Mejorar la metodologia de ingesta de PDFs

Mejorar la forma en la cual se indexan los pdfs dentro de elasticsearch (aproach productivo)

PDF
 ↓
unstructured (mejor parsing)
 ↓
chunking (500 tokens + overlap)
 ↓
Python indexer (bulk)
 ↓
ELSER ingest pipeline (igual que ahora)
 ↓
Elasticsearch (sparse_vector + metadata)
 ↓
Hybrid search (BM25 + text_expansion)
 ↓
IBM Orchestrate agent
 ↓
LLM (RAG)

Para ir tener un pipeline simil a un entorno productivo vas a necesitar:
- Reemplazar pypdf por unstructured
- Agregar chunking por texto en vez de por pagina de 300 a 800 tokens con un 10%-20% de overlap
- Implementar indexado por bulk
- Mejorar  el mapping
- Aplicar queries hibridas sobre elasticsearch en orquestrate


## Extra 4 — Comparar estrategias de búsqueda en Dev Tools

Corré estas tres queries sobre `kb-ai-docs` en **Kibana → Dev Tools** y compará los top-5.

**BM25 puro (léxico):**
```
GET kb-ai-docs/_search
{
  "size": 5,
  "query": { "match": { "contenido": "<tu-pregunta>" } }
}
```

**ELSER puro (semántico):**
```
GET kb-ai-docs/_search
{
  "size": 5,
  "query": {
    "text_expansion": {
      "contenido_embedding": {
        "model_id": ".elser_model_2_linux-x86_64",
        "model_text": "<tu-pregunta>"
      }
    }
  }
}
```

**Híbrida con RRF:**
```
GET kb-ai-docs/_search
{
  "size": 5,
  "retriever": {
    "rrf": {
      "retrievers": [
        { "standard": { "query": { "match": { "contenido": "<tu-pregunta>" } } } },
        { "standard": { "query": { "text_expansion": { "contenido_embedding": {
              "model_id": ".elser_model_2_linux-x86_64",
              "model_text": "<tu-pregunta>"
        } } } } }
      ]
    }
  }
}
```

**Reto:** encontrá una pregunta donde BM25 gane claramente (términos exactos, siglas) y otra donde ELSER gane (sinónimos, paráfrasis). Anotá cuál elegirías para este dataset.

## Extra 5 — Mini golden set de evaluación

Armá 5 preguntas con respuesta conocidas viendo los pdf o la web que crawleaste, corrélas contra el agente y anotá cuántas respondió bien, cuántas alucinó y cuántas citó mal la fuente. Es el mínimo viable de evaluación de RAG que vimos en teoría.

---

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| El crawler no indexa nada | El sitio bloquea bots, o falta validar el dominio | Cambiar de dominio, validar en Manage Domains |
| Docs del crawler sin `body_embedding` | El pipeline ML no se asoció antes del crawl | Revisar Pipelines → ML inference pipeline y re-crawlear |
| Orchestrate no valida la conexión a Elastic | Endpoint o API key mal copiados | Regenerar API key, revisar espacios en blanco |
| El agente responde de memoria sin citar | System prompt mal configurado o KB no asociada | Revisar instrucciones y linkeo de KB |
| "No encontré información" para preguntas que sí están | Campo de texto/embedding mal configurado en la KB | Revisar la config de la KB en Orchestrate |
| ELSER devuelve `model not deployed` | El modelo no está started a nivel cluster | Avisar al instructor |
