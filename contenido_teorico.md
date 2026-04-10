# Workshop Watsonx — Guía teórica

Este documento cubre los conceptos necesarios para los tres días del workshop. Está pensado como referencia durante y después de las sesiones: podés volver a consultarlo cuando estés trabajando en los ejercicios o cuando algo no quede claro.


## DIA 1


## Conceptos de IA


### Cómo funciona un LLM

#### Tokens

Un LLM no lee palabras, lee tokens. Un token es aproximadamente una sílaba o palabra corta en inglés. En español los textos consumen más tokens por la morfología del idioma, lo que tiene impacto directo en costos y en el espacio disponible en el contexto.

Cuando llamás a la API tenés un límite de tokens por request. Si tu system prompt tiene 2.000 tokens y el contexto del usuario otros 1.000, el modelo solo tiene el espacio restante para generar la respuesta.

Podés estimar tokens en: [platform.openai.com/tokenizer](https://platform.openai.com/tokenizer)

#### Context window

El modelo solo "ve" lo que está dentro de su ventana de contexto. No tiene memoria entre llamadas a menos que se la pases explícitamente. Todo lo que querés que recuerde tiene que estar en el prompt.

#### Temperatura

Controla qué tan determinista o creativo es el modelo:

- `0.0` — siempre la respuesta más probable. Para extracción de datos, clasificación, código.
- `0.5 - 0.8` — balance. Para resúmenes y respuestas conversacionales.
- `1.0+` — más variedad y creatividad, más riesgo de errores. Para brainstorming y texto libre.

En producción, los agentes trabajan con temperatura baja. Un agente que toma decisiones no debe improvisar.

#### Tipos de modelo: base vs instruct vs chat

| Tipo | Comportamiento | Uso típico |
|---|---|---|
| Base | Completa texto. No sigue instrucciones. | Fine-tuning, investigación |
| Instruct | Sigue instrucciones directas. Sin historial. | Tareas puntuales, pipelines |
| Chat | Conversación multi-turno. Entiende roles system/user/assistant. | Agentes, asistentes |

En watsonx.ai van a usar principalmente modelos instruct y chat. El tipo de modelo cambia cómo se estructura el prompt.

#### Por qué los modelos alucinan

Los LLMs no saben cosas, predicen el token más probable dado el contexto. Cuando no tienen información suficiente, generan la respuesta estadísticamente más plausible aunque sea incorrecta.

Las tres causas más frecuentes en producción:

1. El modelo no tiene la información en su contexto — solución: RAG (Día 3)
2. La instrucción es ambigua — solución: prompt engineering claro (Día 2)
3. Temperatura alta en tareas de extracción — solución: bajar temperatura (Día 2)

Mitigaciones concretas:
- Incluir en el system prompt: "Si no tenés información suficiente, respondé NO_SE. No inventes."
- Pedirle que cite la fuente de donde extrae la respuesta
- Validar outputs críticos con una segunda llamada ("¿esta respuesta contradice el contexto dado?")


### Embeddings y búsqueda semántica

#### Qué es un embedding

Un embedding es una representación numérica de un texto: un vector de cientos o miles de números. Los textos con significado similar tienen vectores cercanos en ese espacio.

Si pusieras todas las frases del idioma en un mapa, "el auto está roto" y "el vehículo tiene una falla" quedarían cerca. "El auto está roto" y "mañana llueve" quedarían lejos.

La similitud entre dos vectores se mide con similitud coseno, que da un valor entre -1 y 1.

#### Por qué importa para el Día 3

Cuando construyan la base de conocimiento, los documentos no se guardan como texto: se convierten en embeddings y se almacenan en una base de datos vectorial (Milvus o Elasticsearch).

La cadena completa:

```
Documento → Embedding → Almacenar en Milvus/Elastic
Pregunta  → Embedding → Buscar similares → Recuperar fragmentos → Pasar al LLM → Respuesta
```

Eso se llama RAG (Retrieval Augmented Generation). El LLM no sabe las respuestas, las lee del contexto que le mandás.


### Agentes y herramientas

#### Qué es un agente

Un agente no es un modelo con un nombre. Es un loop donde el modelo puede tomar decisiones, ejecutar acciones y observar resultados, iterativamente, hasta completar una tarea.

La diferencia con un LLM solo:
- LLM solo: recibe un prompt, genera una respuesta, termina.
- Agente: recibe un objetivo, planifica, ejecuta herramientas, evalúa el resultado, ajusta, vuelve a ejecutar.

#### El loop ReAct

```
[Objetivo] → RAZONA que hacer
           → ACTUA (llama una herramienta)
           → OBSERVA el resultado
           → RAZONA de nuevo con la nueva información
           → ... repite hasta completar el objetivo
```

Ejemplo concreto:

```
Tarea:      "¿Cuál es el estado del pedido #1234?"
Razonamiento: Necesito consultar el sistema de órdenes.
Accion:     get_order_status(order_id="1234")
Observacion: {"status": "en camino", "eta": "mañana 15hs"}
Respuesta:  "Tu pedido #1234 está en camino y llegará mañana a las 15hs."
```

#### Tools y Function Calling

Las herramientas son funciones que el agente puede invocar. El modelo no las ejecuta directamente: decide que necesita llamar una función, el runtime la ejecuta, y le devuelve el resultado.

Las tools se definen como funciones Python con type hints y docstrings. El modelo lee esa descripción para decidir cuándo y cómo llamarla. La calidad del docstring impacta directamente en qué tan bien el agente usa sus herramientas.

#### Multi-agente

Un agente único tiene límites: contexto finito, responsabilidades acotadas, acoplamiento entre capacidades. Cuando la tarea es compleja, conviene tener un agente orquestador que delega subtareas a agentes especializados.

```
Agente Orquestador
├── recibe el objetivo de alto nivel
├── decide que sub-agente necesita
├── delega la tarea
├── recibe el resultado
└── continúa o delega a otro agente

Agente A (especialista en datos)
Agente B (especialista en comunicaciones)
```

El orquestador no resuelve tareas: decide quién las resuelve y en qué orden. Esto es lo que van a implementar con Watsonx Orchestrate en el Día 2.


### Prompt Engineering

#### Los tres roles

```python
messages = [
    {"role": "system",    "content": "Instrucciones permanentes del agente"},
    {"role": "user",      "content": "Input del usuario"},
    {"role": "assistant", "content": "Respuesta anterior (historial)"}
]
```

El system prompt es el más importante. Define el comportamiento, los límites, el formato de respuesta y el contexto del agente. Un buen system prompt puede hacer más diferencia que cambiar de modelo.

#### Patron 1 — Output estructurado

Cuando necesitás que el agente devuelva datos procesables, no texto libre:

```
Respondé SIEMPRE con un JSON válido con este esquema exacto:
{"categoria": str, "prioridad": "baja|media|alta|critica", "resumen": str}
No incluyas texto fuera del JSON.
```

#### Patron 2 — Chain of Thought

Cuando la tarea requiere razonamiento en pasos:

```
Antes de responder, razoná paso a paso entre etiquetas <thinking>.
Luego dá tu respuesta final entre etiquetas <answer>.
```

Mejora la precisión en tareas de análisis y reduce errores en agentes que toman decisiones.

#### Patron 3 — Few-shot

Ejemplos de comportamiento esperado en lugar de (o además de) describirlo:

```
Input: "La app no carga"         → Output: {"categoria": "UI", "prioridad": "media"}
Input: "Perdimos datos de prod"  → Output: {"categoria": "DATA", "prioridad": "critica"}
Input: "El login tarda 30s"      → Output: {"categoria": "PERFORMANCE", "prioridad": "alta"}

Ahora clasificá: "El login falla para usuarios con caracteres especiales"
```

#### Patron 4 — Manejo de incertidumbre

Siempre incluir en agentes de producción:

```
Si no tenés información suficiente para responder con seguridad,
respondé exactamente: NO_SE. No inventes información.
```


## IBM Cloud: modelo mental del entorno

### La jerarquía

```
IBM Cloud Account
└── Resource Group  (agrupación lógica, como un namespace)
    ├── Instancia: watsonx.ai
    ├── Instancia: watsonx.data
    ├── Instancia: Elasticsearch
    └── Instancia: Watsonx Orchestrate

Dentro de watsonx.Orchestrate:
    └── Workspace
        ├── Agentes
        ├── Tools
        └── Knowledge

Dentro de watsonx.ai:
    └── Proyecto
        ├── Modelos
        ├── Notebooks
        └── Deployments
```

**Resource Group**: carpeta lógica para agrupar servicios. Sirve para gestión de accesos y facturación.

**Instancia vs Proyecto**: la instancia es el servicio aprovisionado en IBM Cloud. El proyecto es el espacio de trabajo dentro de watsonx.ai. Una instancia puede tener múltiples proyectos.

### Watsonx como SaaS

Watsonx no se instala ni se hostea. Es un conjunto de servicios que IBM opera, consumibles vía API.

Lo que controlamos:
- Qué modelo usamos
- Cómo armamos los prompts
- Qué datos le pasás
- Cómo integrás la API en tus sistemas

### IAM: credenciales y accesos

| Credencial | Qué es | Cuándo se usa |
|---|---|---|
| API Key | Clave asociada a un usuario o Service ID | Para autenticar llamadas desde código |
| IAM Token | Token temporal generado desde la API Key | El SDK lo maneja automáticamente |

Flujo de autenticación:

```
API Key → POST iam.cloud.ibm.com/identity/token → IAM Token (expira en 1h)
                                                 → Se usa en cada llamada a la API
```

El SDK de watsonx en Python maneja el refresh del token automáticamente. Solo necesitás pasar la API Key una vez al inicializar el cliente.


## Onboarding: servicios del workshop

### Watsonx Orchestrate

Tour por la interfaz:
- Panel de agentes y catálogo de herramientas
- Abrir un agente existente y leer su definición YAML
- Ver cómo están declaradas las tools y la knowledge base
- Interactuar con el agente desde el chat integrado

La integración vía código y el ADK se desarrollan en el Día 2.

### watsonx.ai

1. Acceder a `cloud.ibm.com` → Resource Group del workshop → instancia de watsonx.ai
2. Crear un proyecto propio (nombre-apellido-onboard)
3. Explorar el Prompt Lab: modelo, temperatura, max tokens, system prompt
4. Generar la API Key desde IAM y guardarla — no se puede recuperar después
5. Verificar con el script `01_watsonx_setup.py`

### SDK Python

El SDK `ibm-watsonx-ai` está instalado en el entorno Docker. Para inicializar el cliente:

```python
from ibm_watsonx_ai import APIClient, Credentials

client = APIClient(Credentials(url=WX_URL, api_key=WX_API_KEY))
```

Verificar con el script `02_sdk_prompts.py`.

### Elasticsearch

Cluster provisionado en IBM Cloud. Credenciales en el `.env` del repo.

El índice `workshop_docs` tiene esta estructura:

```json
{
  "mappings": {
    "properties": {
      "contenido":  { "type": "text" },
      "embedding":  { "type": "dense_vector", "dims": 384 },
      "fuente":     { "type": "keyword" }
    }
  }
}
```

Verificar con el script `03_elasticsearch.py`.


## DIA 2

## Watsonx Orchestrate: orquestación de agentes

### Por qué un agente standalone no escala

Un agente único acumula tres problemas a medida que crece:

**Contexto limitado**: si el agente maneja todo, el contexto se llena con información irrelevante para cada subtarea.

**Complejidad acoplada**: agregar una nueva capacidad implica modificar el agente central, sus tools y su system prompt.

**Trazabilidad difícil**: cuando algo falla en un agente con diez tools, encontrar el paso que falló es costoso.

La solución es la misma que en arquitectura de software: separación de responsabilidades.

### El modelo de orquestación

```
Usuario
  |
  v
Agente Orquestador  <- tiene el objetivo completo, gestiona el flujo
  |-- evalua que necesita
  |-- delega al Agente A
  |     └── Agente A ejecuta, devuelve resultado
  |-- procesa el resultado
  |-- delega al Agente B
  |     └── Agente B ejecuta, devuelve resultado
  └── sintetiza y responde al usuario
```

El orquestador no resuelve tareas: decide quién las resuelve y en qué orden.

Ventajas:
- Cada agente se desarrolla, testea y versiona de forma independiente
- Se puede reemplazar un agente sin tocar el orquestador
- El historial de decisiones del orquestador es auditable
- Se pueden agregar agentes nuevos sin modificar los existentes

### Orchestrate vs implementación manual

Orchestrate hace declarativamente lo que de otra forma requeriría código de infraestructura:

- **Catálogo de agentes**: registra qué agentes existen y qué capacidades tienen
- **YAML de definición**: especifica el comportamiento del agente sin código
- **ADK** (Agent Development Kit): importa agentes externos al ecosistema y permite cambiar el modelo subyacente
- **Canales**: Slack, web, API — conectan el orquestador con el exterior sin código adicional

### Estructura de un YAML en Orchestrate

```yaml
spec_version: v1
style: default
name: agente_soporte
description: |
  Clasifica y escala tickets de soporte técnico.

llm: watsonx/meta-llama/llama-3-3-70b-instruct

instructions: |
  Clasificá el ticket recibido y devolvé un JSON con categoria y prioridad.
  Si no podés clasificar: {"categoria": "DESCONOCIDO", "prioridad": "media"}

tools:
  - name: consultar_base_conocimiento
    description: Busca en la base de conocimiento interna
  - name: crear_ticket
    description: Crea el ticket en el sistema de gestión

knowledge_base:
  - name: kb_soporte
    description: Procedimientos y resoluciones previas
```


## DIA 3


## Base de conocimiento: RAG con Elasticsearch

### El problema que resuelve una base de conocimiento

Los LLMs tienen dos limitaciones para uso empresarial:

1. **Conocimiento con fecha de corte**: no saben nada de lo que ocurrió después de su entrenamiento.
2. **Dominio privado desconocido**: no tienen acceso a documentos internos ni procesos de la empresa.

La solución es darle al modelo la información en el momento en que la necesita, dentro del contexto del prompt. Eso es RAG.

### RAG: Retrieval Augmented Generation

```
FASE DE INDEXACION (una vez, o cuando cambian los documentos)
Documentos → Chunking → Embedding → Almacenar en base vectorial

FASE DE CONSULTA (en cada pregunta del usuario)
Pregunta → Embedding → Buscar chunks similares → Recuperar los top-K
         → Construir prompt: [system] + [chunks recuperados] + [pregunta]
         → LLM genera respuesta basada en ese contexto
```

El LLM nunca accede a la base de datos directamente. Recibe los fragmentos relevantes como parte del prompt.

### Chunking

| Estrategia | Cuándo usarla |
|---|---|
| Por tamaño fijo (ej: 512 tokens) | Documentos homogéneos sin estructura |
| Por separadores (párrafos, secciones) | Documentos con estructura (manuales, wikis) |
| Semántico (por coherencia de tema) | Cuando la precisión de recuperación es crítica |
| Con overlap | Para no perder contexto en los bordes del chunk |

Parámetros típicos de producción: chunks de 256-512 tokens con overlap de 50-100 tokens.

### Elasticsearch en el contexto de RAG

**Búsqueda léxica (BM25)**: busca documentos que contienen las palabras del query. Efectivo para términos técnicos exactos, nombres propios y códigos. No entiende sinónimos.

**Búsqueda semántica (kNN)**: busca por similitud de embeddings. Encuentra resultados relevantes aunque las palabras no coincidan. Puede traer falsos positivos si los embeddings no están bien calibrados.

**Búsqueda híbrida** (recomendada para producción):

```
score_final = α × score_bm25 + (1-α) × score_vectorial
```

### Milvus en el contexto de RAG (Fuera del scope del workshop)

| Criterio | Elasticsearch | Milvus |
|---|---|---|
| Volumen de vectores | Millones | Decenas o cientos de millones |
| Búsqueda híbrida text+vector | Nativa y madura | Requiere más configuración |
| Operaciones vectoriales avanzadas | Básico | Avanzado |
| Integración con datos tabulares | No | Sí, via watsonx.data |
| Latencia a escala masiva | Degradación | Optimizada |

Para la mayoría de los casos empresariales a escala moderada, Elasticsearch híbrido es suficiente. Milvus entra cuando el volumen o las operaciones vectoriales superan las capacidades de Elasticsearch.

**Milvus en watsonx.data**: capa de gobernanza sobre Milvus. Permite administrar colecciones junto con otros data sources y aplicar políticas de acceso unificadas.

Estructura de una colección:

```
Coleccion: documentos_empresa
├── id          (INT64, primary key)
├── contenido   (VARCHAR, el texto del chunk)
├── embedding   (FLOAT_VECTOR, dims=384)
└── metadata    (JSON, fuente, fecha, tags)
```

### Arquitectura completa

```
                    ┌─────────────────────────────────┐
                    │         watsonx.ai               │
                    │  (LLM genera la respuesta final) │
                    └──────────────┬──────────────────┘
                                   │ prompt con contexto
                    ┌──────────────▼──────────────────┐
                    │      Pipeline RAG                 │
                    │  1. embed query                   │
                    │  2. buscar en base vectorial      │
                    │  3. construir prompt              │
                    └──────┬───────────────┬──────────┘
                           │               │
             ┌─────────────▼──┐    ┌───────▼────────────┐
             │  Elasticsearch  │    │  Milvus/watsonx.data│
             │  (busqueda      │    │  (busqueda vectorial│
             │   hibrida)      │    │   a escala)         │
             └────────────────┘    └────────────────────┘
```

### Buenas practicas

**En la indexación:**
- Limpiar el texto antes de chunkear: eliminar headers/footers repetitivos y contenido irrelevante
- Incluir metadata en cada chunk (fuente, sección, fecha) para poder filtrar en la búsqueda
- Usar el mismo modelo de embedding para indexar y para hacer queries. Un cambio de modelo invalida todo el índice.

**En la búsqueda:**
- Empezar con búsqueda híbrida y ajustar el peso α según el caso
- Recuperar más chunks de los necesarios (top-10 o top-20) y reranquear antes de pasar al LLM
- Limitar el total de tokens de contexto recuperado para no saturar la ventana del modelo

**En el prompt del LLM:**
- Indicar explícitamente que solo responda basándose en el contexto provisto
- Pedir que cite el fragmento o la fuente de donde extrajo la información
- Manejar el caso "no encontré información relevante" antes de llegar al LLM
