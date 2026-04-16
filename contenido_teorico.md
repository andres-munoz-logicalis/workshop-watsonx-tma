# Workshop Watsonx — Guía teórica

## Cómo usar esta guía

Esta guía cubre los conceptos teóricos de los tres días del workshop.

**Cómo leerla:**
- **Antes del workshop:** leé el Día 1 completo. Es la base que necesitás para los hands-on.
- **Durante el workshop:** usala como referencia rápida cuando algo no quede claro.
- **Después:** queda como backup en el repo. Volvé cuando estés implementando algo.

**Prerequisitos asumidos:** sabés qué es una API REST, ya usaste algún LLM (vía API o playground), tenés noción básica de Python.

---

## DÍA 1

**Objetivos del día:**
- Refrescar conceptos clave de LLMs, agentes y prompting
- Entender el modelo mental de IBM Cloud y Watsonx
- Tener el entorno funcionando para el primer hands-on

---

## 1. Conceptos de IA

### 1.1 Cómo funciona un LLM

#### Tokens

Un LLM no lee palabras, lee tokens. Un token es aproximadamente una sílaba o palabra corta en inglés. En español los textos consumen más tokens por la morfología del idioma, lo que impacta directamente en costos y en el espacio del contexto.

Por qué importa más allá del costo: los límites de contexto se cuentan en tokens, no en caracteres, y los modelos **truncan silenciosamente** cuando se pasan. Cada familia de modelos usa su propio tokenizer (Llama tokeniza distinto que GPT), así que un mismo texto puede tener distinto conteo.

Estimador: [platform.openai.com/tokenizer](https://platform.openai.com/tokenizer) sirve como referencia general aunque uses otros modelos.

#### Context window

El modelo solo "ve" lo que está dentro de su ventana de contexto. **No tiene memoria entre llamadas** a menos que se la pases explícitamente. Todo lo que querés que recuerde tiene que estar en el prompt.

#### Temperatura y top_p

La temperatura controla qué tan determinista o creativo es el modelo:

- `0.0` — siempre la respuesta más probable. Para extracción, clasificación, código, agentes.
- `0.5 - 0.8` — balance. Para resúmenes y respuestas conversacionales.
- `1.0+` — más variedad y creatividad, más riesgo. Para brainstorming y texto libre.

`top_p` (nucleus sampling) es complementario: limita el muestreo a los tokens cuya probabilidad acumulada llega a `p`. Se usan en conjunto, no como reemplazo. En producción, lo más común es bajar `temperature` y dejar `top_p` en su default.

En agentes, **siempre temperatura baja**. Un agente que toma decisiones no debe improvisar.

#### Tipos de modelo: base vs instruct vs chat

| Tipo | Comportamiento | Uso típico |
|---|---|---|
| Base | Completa texto. No sigue instrucciones. | Fine-tuning, investigación |
| Instruct | Sigue instrucciones directas. Sin historial. | Tareas puntuales, pipelines |
| Chat | Conversación multi-turno. Roles system/user/assistant. | Agentes, asistentes |

En watsonx.ai vas a ver nombres como `llama-3-3-70b-instruct`. El sufijo te dice qué tipo es.

#### Por qué los modelos alucinan

Los LLMs no saben cosas, predicen el token más probable dado el contexto. Cuando no tienen información suficiente, generan la respuesta estadísticamente más plausible aunque sea incorrecta.

Causas frecuentes en producción:

1. **Falta información en el contexto** → solución: RAG (Día 3)
2. **Instrucción ambigua** → solución: prompt engineering claro
3. **Temperatura alta en tareas de extracción** → solución: bajarla a 0
4. **El modelo inventa argumentos de tools que no existen** → solución: validar el schema antes de ejecutar la tool

Mitigaciones concretas:
- En el system prompt: *"Si no tenés información suficiente, respondé NO_SE. No inventes."*
- Pedirle que cite la fuente de donde extrae la respuesta
- Validar outputs críticos con una segunda llamada de verificación

**Auto-chequeo:**
1. ¿Por qué bajamos la temperatura en agentes?
2. ¿Qué pasa si tu prompt + contexto excede el context window?
3. ¿Cuál es la diferencia funcional entre un modelo instruct y uno chat?

---

### 1.2 Embeddings y búsqueda semántica

Un **embedding** es una representación numérica de un texto: un vector de cientos o miles de números. Los textos con significado similar tienen vectores cercanos en ese espacio.

Si pusieras todas las frases del idioma en un mapa, *"el auto está roto"* y *"el vehículo tiene una falla"* quedarían cerca. *"El auto está roto"* y *"mañana llueve"* quedarían lejos.

La similitud entre dos vectores se mide con **similitud coseno**, que da un valor entre -1 y 1.

#### Por qué importa para el Día 3

Cuando construyan la base de conocimiento, los documentos no se guardan como texto: se convierten en embeddings y se almacenan en una base vectorial (Elasticsearch o Milvus).

```
Documento → Embedding → Almacenar en Elastic/Milvus
Pregunta  → Embedding → Buscar similares → Recuperar fragmentos → Pasar al LLM → Respuesta
```

Eso es **RAG** (Retrieval Augmented Generation). El LLM no sabe las respuestas, las lee del contexto que le mandás.

Tenés que usar el **mismo modelo de embedding** para indexar y para hacer queries. Un cambio de modelo invalida todo el índice.

---

### 1.3 Agentes y herramientas

#### Qué es un agente

Un agente no es un modelo con un nombre. Es un **loop** donde el modelo puede tomar decisiones, ejecutar acciones y observar resultados, iterativamente, hasta completar una tarea.

- **LLM solo:** recibe un prompt, genera una respuesta, termina.
- **Agente:** recibe un objetivo, planifica, ejecuta herramientas, evalúa el resultado, ajusta, vuelve a ejecutar.

#### El loop ReAct (Reason + Act)

```
[Objetivo] → RAZONA qué hacer
           → ACTÚA (llama una herramienta)
           → OBSERVA el resultado
           → RAZONA de nuevo con la nueva información
           → ... repite hasta completar el objetivo
```

Ejemplo:

```
Tarea:        "¿Cuál es el estado del pedido #1234?"
Razonamiento: Necesito consultar el sistema de órdenes.
Acción:       get_order_status(order_id="1234")
Observación:  {"status": "en camino", "eta": "mañana 15hs"}
Respuesta:    "Tu pedido #1234 está en camino y llega mañana a las 15hs."
```

#### Cuándo NO usar un agente

Esto importa porque los agentes son caros e impredecibles comparados con un LLM con prompt fijo. **No uses un agente cuando:**

- La tarea es determinística (ej: "extraer estos 5 campos de un texto"). Un LLM con prompt estructurado es más barato, más rápido y más confiable.
- No hay decisiones condicionales ni múltiples herramientas posibles.
- La latencia importa mucho: cada iteración del loop es una llamada al LLM.

Los agentes valen la pena cuando hay **decisiones condicionales reales** o **múltiples herramientas** entre las que elegir según el contexto.

#### Tools y Function Calling

Las herramientas son funciones que el agente puede invocar. El modelo no las ejecuta directamente: **decide** que necesita llamar una función, el runtime la ejecuta, y le devuelve el resultado.

Las tools se definen como funciones Python con type hints y docstrings. **El modelo lee esa descripción** para decidir cuándo y cómo llamarla. La calidad del docstring impacta directamente en qué tan bien el agente usa sus herramientas.

#### Errores comunes en tools

- **Tool que devuelve un error y el agente lo ignora o lo loopea infinito.** Solución: límites de iteraciones del loop + mensajes de error procesables (*"la API devolvió 404, el recurso no existe, no reintentes con el mismo ID"*).
- **El agente alucina argumentos** que la tool no acepta. Solución: validar el schema del input antes de ejecutar.
- **Tool muy genérica.** Una tool `query_database(sql)` deja todo el peso en el modelo. Mejor descomponer en `get_user_by_id`, `list_orders`, etc.

#### Costo del loop

Cada iteración del loop ReAct es **una llamada al LLM**. Un agente que itera 10 veces cuesta 10x un LLM call simple. Esto importa cuando vean facturación en producción. Siempre poner un límite máximo de iteraciones (típicamente 5-10).

#### Multi-agente

Un agente único tiene límites: contexto finito, responsabilidades acotadas, acoplamiento entre capacidades. Cuando la tarea es compleja, conviene tener un **agente orquestador** que delega subtareas a agentes especializados.

```
Agente Orquestador
├── recibe el objetivo de alto nivel
├── decide qué sub-agente necesita
├── delega la tarea
├── recibe el resultado
└── continúa o delega a otro agente
```

El orquestador no resuelve tareas: decide quién las resuelve y en qué orden. Esto es lo que van a implementar con Watsonx Orchestrate en el Día 2.

**Auto-chequeo:**
1. ¿En qué caso preferirías un LLM con prompt fijo en lugar de un agente?
2. ¿Por qué importa tanto el docstring de una tool?
3. ¿Qué pasa si no ponés un límite de iteraciones al loop ReAct?

---

### 1.4 Prompt Engineering

#### Los tres roles

```python
messages = [
    {"role": "system",    "content": "Instrucciones permanentes del agente"},
    {"role": "user",      "content": "Input del usuario"},
    {"role": "assistant", "content": "Respuesta anterior (historial)"}
]
```

El **system prompt** es el más importante. Define comportamiento, límites, formato de respuesta y contexto. Un buen system prompt puede hacer más diferencia que cambiar de modelo.

**Lost in the middle:** los modelos prestan más atención al inicio y al final del prompt que al medio. Poné las instrucciones críticas al final del system prompt.

#### Patrón base: Role + Task + Constraints + Format

Es la plantilla más usada en producción:

```
Sos un [rol].
Tu tarea es [task].
Restricciones: [lista de qué puede y qué no puede hacer].
Formato de respuesta: [esquema exacto].
```

#### Patrón 1 — Output estructurado

Cuando necesitás datos procesables, no texto libre:

```
Respondé SIEMPRE con un JSON válido con este esquema exacto:
{"categoria": str, "prioridad": "baja|media|alta|critica", "resumen": str}
No incluyas texto fuera del JSON.
```

#### Patrón 2 — Chain of Thought

Cuando la tarea requiere razonamiento en pasos:

```
Antes de responder, razoná paso a paso entre etiquetas <thinking>.
Luego dá tu respuesta final entre etiquetas <answer>.
```

Mejora la precisión en análisis y reduce errores en agentes que toman decisiones.

#### Patrón 3 — Few-shot

Ejemplos de comportamiento esperado en lugar de (o además de) describirlo:

```
Input: "La app no carga"         → Output: {"categoria": "UI", "prioridad": "media"}
Input: "Perdimos datos de prod"  → Output: {"categoria": "DATA", "prioridad": "critica"}
Input: "El login tarda 30s"      → Output: {"categoria": "PERFORMANCE", "prioridad": "alta"}

Ahora clasificá: "El login falla para usuarios con caracteres especiales"
```

#### Patrón 4 — Manejo de incertidumbre

Siempre incluir en agentes de producción:

```
Si no tenés información suficiente para responder con seguridad,
respondé exactamente: NO_SE. No inventes información.
```

**Auto-chequeo:**
1. ¿Dónde conviene poner las instrucciones más críticas en un prompt largo?
2. ¿Cuándo usarías few-shot en lugar de describir la tarea?

---

## 2. IBM Cloud: modelo mental del entorno

### La jerarquía

```
IBM Cloud Account
└── Resource Group  (agrupación lógica, como un namespace)
    ├── Instancia: watsonx.ai
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

**Resource Group:** carpeta lógica para gestión de accesos y facturación.
**Instancia vs Proyecto:** la instancia es el servicio aprovisionado en IBM Cloud. El proyecto es el espacio de trabajo dentro de watsonx.ai. Una instancia puede tener múltiples proyectos.

### Watsonx como SaaS

Watsonx no se instala ni se hostea. Es un conjunto de servicios que IBM opera, consumibles vía API. Lo que controlamos: qué modelo usamos, cómo armamos los prompts, qué datos le pasamos, cómo integramos la API.

### IAM: credenciales y accesos

| Credencial | Qué es | Cuándo se usa |
|---|---|---|
| API Key | Clave asociada a un usuario o Service ID | Autenticar llamadas desde código |
| IAM Token | Token temporal generado desde la API Key | El SDK lo maneja automáticamente |

```
API Key → POST iam.cloud.ibm.com/identity/token → IAM Token (expira en 1h)
                                                 → Se usa en cada llamada a la API
```

El SDK maneja el refresh automáticamente. Pasás la API Key una vez al inicializar el cliente.

**Service ID vs API key personal:** para apps en producción usá Service IDs (asociados a una identidad de servicio, no a un usuario). En el workshop usamos API keys personales por simplicidad.

### Troubleshooting de credenciales

| Error | Causa probable | Solución |
|---|---|---|
| 401 Unauthorized | API key vencida, mal copiada o con espacios | Regenerar la key, copiar limpia |
| 403 Forbidden | La key existe pero no tiene rol sobre el resource group | Pedir permisos al admin |
| 404 en project_id | Apuntando a otra región o proyecto inexistente | Verificar `WX_URL` y `PROJECT_ID` |
| Timeout | Problema de red o proxy | Verificar conectividad a `*.cloud.ibm.com` |

---

## 3. Onboarding: servicios del workshop

### Watsonx Orchestrate

Tour por la interfaz:
- Panel de agentes y catálogo de herramientas
- Abrir un agente existente y leer su YAML
- Ver cómo están declaradas las tools y la knowledge base
- Interactuar con el agente desde el chat integrado

### watsonx.ai

1. Acceder a `cloud.ibm.com` → Resource Group del workshop → instancia de watsonx.ai
2. Crear un proyecto propio (`nombre-apellido-onboard`)
3. Explorar el Prompt Lab: modelo, temperatura, max tokens, system prompt
4. Generar la API Key desde IAM y guardarla — **no se puede recuperar después**
5. Verificar con `01_watsonx_setup.py`

### SDK Python

```python
from ibm_watsonx_ai import APIClient, Credentials
client = APIClient(Credentials(url=WX_URL, api_key=WX_API_KEY))
```

Verificar con `02_sdk_prompts.py`.

### Elasticsearch

Cluster provisionado en IBM Cloud. Credenciales en el `.env`. Índice `workshop_docs`:

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

Verificar con `03_elasticsearch.py`.

---

## DÍA 2

**Objetivos del día:**
- Entender por qué se orquestan agentes en lugar de hacer uno solo gigante
- Leer y escribir definiciones YAML de agentes en Orchestrate
- Usar el ADK para integrar agentes externos

---

## 4. Watsonx Orchestrate: orquestación de agentes

### Puente con el Día 1

En el Día 1 vimos qué es un agente y cómo funciona el loop ReAct. Hoy vemos **por qué un agente solo no alcanza** cuando el sistema crece, y cómo Orchestrate resuelve la composición de múltiples agentes.

### Por qué un agente standalone no escala

Un agente único acumula tres problemas:

- **Contexto limitado:** si maneja todo, el contexto se llena con info irrelevante para cada subtarea.
- **Complejidad acoplada:** agregar una capacidad implica modificar el agente central, sus tools y su prompt.
- **Trazabilidad difícil:** cuando algo falla en un agente con diez tools, encontrar el paso que falló es costoso.

La solución es la misma que en arquitectura de software: **separación de responsabilidades**.

### El modelo de orquestación

```
Usuario
  |
  v
Agente Orquestador  <- tiene el objetivo completo, gestiona el flujo
  |-- evalúa qué necesita
  |-- delega al Agente A → ejecuta, devuelve resultado
  |-- procesa el resultado
  |-- delega al Agente B → ejecuta, devuelve resultado
  └── sintetiza y responde al usuario
```

Ventajas:
- Cada agente se desarrolla, testea y versiona de forma independiente
- Se puede reemplazar un agente sin tocar el orquestador
- El historial de decisiones del orquestador es auditable
- Se agregan agentes nuevos sin modificar los existentes

### Cómo decide el orquestador a quién delegar

El orquestador lee las **`description`** de los agentes registrados y elige basándose en match semántico con la tarea entrante. Por eso la `description` de un agente es **tan importante como su prompt**: si está mal redactada, el orquestador no lo va a invocar nunca o lo va a invocar mal.

Error frecuente: confundir `instructions` (el system prompt del agente) con `description` (lo que el orquestador lee para decidir si delegar). Son cosas distintas.

### Orchestrate vs implementación manual

Orchestrate hace declarativamente lo que de otra forma requeriría código de infraestructura:

- **Catálogo de agentes:** registra qué agentes existen y qué capacidades tienen
- **YAML de definición:** especifica el comportamiento sin código
- **ADK** (Agent Development Kit): importa agentes externos al ecosistema y permite cambiar el modelo subyacente
- **Canales:** Slack, web, API — conectan el orquestador con el exterior sin código

### Anatomía de un YAML en Orchestrate

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

| Campo | Qué hace |
|---|---|
| `spec_version` | Versión del schema de Orchestrate. Importante para compatibilidad. |
| `style` | Estilo de razonamiento del agente (default, react, etc.) |
| `name` | Identificador único dentro del workspace |
| `description` | **Lo que lee el orquestador** para decidir delegar a este agente |
| `llm` | Modelo subyacente, formato `provider/modelo` |
| `instructions` | **System prompt del agente** (no confundir con description) |
| `tools` | Lista de herramientas que puede invocar |
| `knowledge_base` | Bases de conocimiento que puede consultar |

**Auto-chequeo:**
1. ¿Cuál es la diferencia entre `description` e `instructions` en un YAML de agente?
2. ¿Qué problema concreto resuelve tener un agente orquestador vs uno solo grande?

---

## DÍA 3

**Objetivos del día:**
- Entender RAG y cuándo aplicarlo
- Diseñar una base de conocimiento con Elasticsearch
- Conocer alternativas a RAG y sus tradeoffs

---

## 5. Base de conocimiento: RAG con Elasticsearch

### El ecosistema Elastic: qué es cada cosa

Antes de meternos en cómo se usa Elasticsearch para RAG, conviene entender qué es cada pieza del ecosistema Elastic y por qué existe. Muchos devs conocen Elastic solo por el stack ELK (logs), pero hay más cosas en juego.

#### Elasticsearch

Es el **motor de búsqueda y almacenamiento** que está en el corazón de todo. No es una base de datos relacional ni un data warehouse: es un motor optimizado para **indexar texto y recuperarlo rápido** a partir de queries.

Internamente funciona con un *inverted index* (como el índice al final de un libro: de cada palabra, qué documentos la contienen). A eso se le sumaron, en versiones recientes, capacidades de búsqueda vectorial (`dense_vector`) para habilitar búsqueda semántica además de la clásica léxica.

Qué guarda: documentos JSON organizados en **índices** (equivalente aproximado a una tabla). Cada documento tiene campos con tipos (`text`, `keyword`, `date`, `dense_vector`, etc.). La estructura se define en el **mapping** del índice.

#### Dense vectors vs Sparse vectors

Cuando hablamos de búsqueda en Elasticsearch para RAG, aparecen dos formas de representar texto como vectores: **dense** y **sparse**. Entender la diferencia es clave para elegir bien la estrategia de retrieval.

##### Dense vectors (vectores densos)

Un `dense_vector` es un vector de números de tamaño fijo (ej: 384, 768, 1536 dimensiones) generado por un modelo de embeddings.

Ejemplo simplificado:
- "El gato duerme en el sillón" → [0.12, -0.98, 0.44, ..., 0.07]

Características:

- Representan el **significado semántico** del texto
- Dos textos con palabras distintas pero mismo significado → vectores similares
- Se usan con búsqueda **kNN (k-nearest neighbors)**

Ejemplo:

- "auto" ≈ "coche"
- "error al compilar" ≈ "falla en build"

Esto es lo que habilita la búsqueda semántica en RAG.

---

##### Sparse vectors (vectores dispersos)

Un `sparse vector` representa texto como un conjunto de términos con pesos, donde la mayoría de las dimensiones son cero.

Es una extensión del modelo clásico de IR (Information Retrieval), como **BM25** o variantes más modernas.

Ejemplo conceptual:
- "error al compilar código" → {"error": 2.1,"compilar": 1.7,"código": 1.3}

Cómo se consulta: vía API REST con un DSL propio en JSON. Hay clientes oficiales en Python, Java, JS, etc.

Para qué se usa en la industria:
- **Búsqueda en productos** (e-commerce, catálogos, wikis internos)
- **Observabilidad** (logs, métricas, traces — el famoso stack ELK)
- **Analytics sobre texto** (sentiment, clustering, detección de anomalías)
- **Bases de conocimiento para RAG** (lo que nos interesa en el workshop)

Características:

- Basados en **términos exactos del texto**
- Muy buenos para:
  - nombres propios
  - códigos de error (`ERR_504`)
  - términos técnicos específicos
- No capturan semántica profunda (no entienden sinónimos por defecto)

En Elasticsearch, esto aparece como:
- BM25 clásico (inverted index)
- Modelos como ELSER (sparse semántico aprendido)

---

##### Diferencias clave

| Aspecto | Dense vector | Sparse vector |
|---|---|---|
| Representación | Lista densa de floats | Diccionario de términos con pesos |
| Captura semántica | ✅ Alta | ⚠️ Limitada (mejora con modelos como ELSER) |
| Coincidencia exacta | ❌ Peor | ✅ Excelente |
| Interpretabilidad | ❌ Difícil | ✅ Más interpretable |
| Casos fuertes | Lenguaje natural | Queries técnicas / exactas |

---

##### ¿Cuándo usar cada uno?

**Usar dense vectors cuando:**

- El usuario pregunta en lenguaje natural
- Hay muchas formas distintas de decir lo mismo
- Querés recall alto (no perder resultados relevantes)

Ejemplos:
- "¿Cómo hago login?" vs "problemas de autenticación"
- FAQs, documentación, soporte

---

**Usar sparse vectors (o BM25) cuando:**

- Importa la coincidencia exacta de términos
- Hay identificadores únicos o técnicos

Ejemplos:
- "NullPointerException"
- "error 403"
- nombres de funciones, endpoints, tablas

---

##### La práctica real: búsqueda híbrida

En sistemas RAG productivos, casi nunca elegís uno solo.

Se combinan:

- **BM25 / sparse → precisión léxica**
- **Dense vectors → semántica**
- score_final = α × score_sparse + (1-α) × score_dense

Esto evita:

- falsos positivos del embedding
- pérdida de resultados por no matchear palabras exactas

Regla práctica:  
**empezá siempre con híbrido y ajustá después con evaluación.**

---

##### Insight importante

Un error común es pensar:

> "dense vector reemplaza a BM25"

No es así.

- Dense mejora **recall semántico**
- Sparse asegura **precisión léxica**

En RAG, necesitás ambas para que el LLM reciba contexto correcto.

#### Kibana

Es la **interfaz gráfica oficial** para Elasticsearch. No tiene lógica propia: todo lo que hace Kibana termina siendo una llamada REST al cluster de Elastic. Es la capa de presentación.

Qué vas a usar de Kibana:
- **Dev Tools → Console:** un editor interactivo para mandar queries al cluster. Es la forma más rápida de explorar un índice, probar un mapping o debuggear una búsqueda que no devuelve lo que esperabas.
- **Discover:** vista tabular de los documentos de un índice, con filtros. Útil para "ver qué hay" en el índice sin escribir una query.
- **Index Management:** gestión visual de los índices, sus mappings y su tamaño.

Qué **no** vamos a ver hoy pero vale saber que existe:
- **Dashboards y visualizaciones:** la razón por la que mucha gente conoce Kibana (gráficos sobre logs, métricas, etc.)

Muchos devs cuando hacen llamados a la API mientraas crear un índice para RAG, abren Kibana en paralelo para ahorra tiempo: cada vez que algo no devuelve lo esperado, se puede usar las Dev Tools y ver el mapping o correr la misma query a mano antes de tocar código.

#### Enterprise Search

Es una **capa más alta** construida sobre Elasticsearch. Hasta acá, Elasticsearch te da el motor crudo: vos definís mappings, escribís queries en su DSL, armás tu pipeline de ingesta. Enterprise Search resuelve ese "work-around" con componentes listos para usar:

- **Connectors:** conectores pre-armados para fuentes típicas (SharePoint, Confluence, Google Drive, Jira, S3, bases de datos). Se configuran y sincronizan automáticamente, sin escribir código de ingesta.
- **Web Crawler:** crawler configurable para indexar sitios web completos sin armar un scraper propio.
- **Search UI / Search Applications:** librería de componentes frontend y un backend de configuración para montar una experiencia de búsqueda (con facets, filtros, highlighting) sin escribir todo el frontend.
- **Relevance tuning sin código:** pesos por campo, sinónimos, boosts, desde una interfaz visual.

Pensalo así: **Elasticsearch es el motor, Enterprise Search es el auto completado**. Si tu caso de uso entra en los connectors/patrones que Enterprise Search ya resuelve, vas a llegar mucho más rápido que armando todo a mano. Si tu caso es custom (como un pipeline RAG muy específico), probablemente termines yendo directo contra la API de Elasticsearch.

**Elejercicio 03 del oboard va directo contra Elasticsearch**, no contra Enterprise Search. Es importante que conozcan la diferencia porque en proyectos reales muchas veces la primera pregunta es *"¿esto lo resolvemos con Enterprise Search o picando codigo contra Elastic?"*.

#### Review herramientas

                ┌──────────────────────────────────┐
                │      Kibana (UI)                 │
                │  Dev Tools, Discover, Dashboards │
                └───────────────┬──────────────────┘
                                │ API REST
                ┌───────────────▼──────────────────┐
                │      Elasticsearch               │
                │  (motor de búsqueda + storage)   │
                │                                  │
                │  - Inverted index (BM25)         │
                │  - Dense vectors (kNN)           │
                │  - Mappings, queries DSL         │
                └───────────────▲──────────────────┘
                                │
                ┌───────────────┴──────────────────┐
                │    Enterprise Search             │
                │  Connectors, crawler, Search UI  │
                │  (abstracción sobre Elastic)     │
                └──────────────────────────────────┘

Kibana le habla a Elasticsearch para mostrarte cosas. Enterprise Search le habla a Elasticsearch para ingestar datos y servir búsquedas. Abajo de todo, siempre está el mismo motor.

#### Cuándo usar qué

| Necesidad | Herramienta |
|---|---|
| Explorar datos, debuggear queries, ver mappings | Kibana (Dev Tools / Discover) |
| Ingestar documentos desde un sistema típico (Confluence, SharePoint, Drive) | Enterprise Search (Connectors) |
| Indexar un sitio web público | Enterprise Search (Web Crawler) |
| Montar una UI de búsqueda con filtros y facets rápido | Enterprise Search (Search UI) |
| Pipeline custom, control total del mapping y la query | Elasticsearch directo (API / SDK) |
| RAG con pipeline custom y control fino del mapping | Elasticsearch directo (API / SDK) |
| RAG con fuentes estándar y setup rápido | Enterprise Search + connectors |

En el hands-on de hoy vamos a usar la interfaz de Kibana y los connectors de Enterprise Search para montar una base de conocimiento sin código. Esto te da una visión rápida de lo que el ecosistema Elastic resuelve out-of-the-box. En proyectos reales donde necesites control fino del pipeline (chunking custom, embeddings propios, queries híbridas afinadas), vas a terminar yendo contra la API de Elasticsearch directamente

### El problema que resuelve

Los LLMs tienen dos limitaciones para uso empresarial:

1. **Conocimiento con fecha de corte:** no saben nada posterior a su entrenamiento.
2. **Dominio privado desconocido:** no acceden a documentos internos ni procesos de la empresa.

La solución es darle al modelo la información en el momento en que la necesita, dentro del contexto del prompt. Eso es **RAG**.

### ¿RAG o alternativas?

RAG no siempre es la respuesta. Antes de implementarlo, considerá:

| Situación | Solución recomendada |
|---|---|
| Documento chico y estable (<10 páginas) | Meté todo en el system prompt, no necesitás RAG |
| Datos muy estructurados (filas, tablas) | SQL/API directa, no RAG |
| Conocimiento estable y de dominio cerrado | Fine-tuning |
| Conocimiento grande, dinámico, citable | **RAG** |
| Necesitás trazabilidad de fuentes | **RAG** (fine-tuning no permite citar) |

### RAG: Retrieval Augmented Generation

```
FASE DE INDEXACIÓN (una vez, o cuando cambian los documentos)
Documentos → Chunking → Embedding → Almacenar en base vectorial

FASE DE CONSULTA (en cada pregunta del usuario)
Pregunta → Embedding → Buscar chunks similares → Recuperar top-K
        → Construir prompt: [system] + [chunks recuperados] + [pregunta]
        → LLM genera respuesta basada en ese contexto
```

El LLM nunca accede a la base de datos directamente. Recibe los fragmentos relevantes como parte del prompt.

### Chunking

| Estrategia | Cuándo usarla |
|---|---|
| Tamaño fijo (ej: 512 tokens) | Documentos homogéneos sin estructura |
| Por separadores (párrafos, secciones) | Documentos con estructura (manuales, wikis) |
| Semántico (por coherencia de tema) | Cuando la precisión importa mucho |
| Con overlap | Para no perder contexto en los bordes |

Parámetros típicos: chunks de 256-512 tokens con overlap de 50-100 tokens.

**Tablas y código se rompen** con chunking ingenuo. Solución: chunking estructural que respete bloques completos.

### Elasticsearch en RAG

- **Búsqueda léxica (BM25):** busca documentos con las palabras del query. Ideal para términos técnicos exactos, nombres propios y códigos. No entiende sinónimos.
- **Búsqueda semántica (kNN):** busca por similitud de embeddings. Encuentra resultados relevantes aunque las palabras no coincidan. Puede traer falsos positivos.
- **Búsqueda híbrida (recomendada):**

```
score_final = α × score_bm25 + (1-α) × score_vectorial
```

`α` típicamente arranca en 0.5 y se ajusta con un set de evaluación. Sin eval set, es adivinar.

### Evaluación de RAG

No deployees RAG sin un mínimo de evaluación. Lo básico:

- **Golden set:** ~50 preguntas con respuestas conocidas. Lo armás a mano una vez.
- **Recall@k:** de los top-k chunks recuperados, ¿está el chunk correcto?
- **Precisión de la respuesta final:** ¿la respuesta del LLM coincide con la esperada?

Cada vez que cambies algo (modelo de embedding, chunking, α), corré el golden set. Sin esto, todo cambio es a ciegas.

### Milvus (fuera de scope, referencia)

| Criterio | Elasticsearch | Milvus |
|---|---|---|
| Volumen de vectores | Millones | Decenas/cientos de millones |
| Búsqueda híbrida | Nativa y madura | Requiere más configuración |
| Operaciones vectoriales avanzadas | Básico | Avanzado |
| Latencia a escala masiva | Degradación | Optimizada |

Para la mayoría de los casos empresariales, **Elasticsearch híbrido alcanza**. Milvus entra cuando el volumen lo justifica.

### Buenas prácticas

**En la indexación:**
- Limpiar el texto antes de chunkear (eliminar headers/footers repetitivos)
- Incluir metadata en cada chunk (fuente, sección, fecha) para filtrar
- Usar el mismo modelo de embedding para indexar y para queries

**En la búsqueda:**
- Empezar con búsqueda híbrida y ajustar `α` con eval set
- Recuperar más chunks de los necesarios (top-10/20) y reranquear
- Limitar el total de tokens recuperados para no saturar la ventana

**En el prompt del LLM:**
- Indicar explícitamente que solo responda basándose en el contexto provisto
- Pedir que cite la fuente
- Manejar el caso "no encontré información relevante" antes de llegar al LLM

**Auto-chequeo:**
1. ¿En qué caso preferirías fine-tuning sobre RAG?
2. ¿Por qué la búsqueda híbrida suele ganarle a una sola estrategia?
3. ¿Qué es un golden set y para qué sirve?

---

## Anexo A — Glosario

| Término | Definición breve |
|---|---|
| **ADK** | Agent Development Kit. SDK de Orchestrate para definir e importar agentes. |
| **BM25** | Algoritmo clásico de búsqueda léxica (ranking por relevancia de palabras). |
| **Chunk** | Fragmento de un documento, unidad de indexación en RAG. |
| **Context window** | Cantidad máxima de tokens que un LLM puede procesar de una vez. |
| **Dense vector** | Vector denso de floats, representación de un embedding. |
| **Embedding** | Vector numérico que representa el significado semántico de un texto. |
| **Few-shot** | Patrón de prompting que incluye ejemplos del comportamiento deseado. |
| **IAM** | Identity and Access Management. Sistema de auth de IBM Cloud. |
| **kNN** | k-Nearest Neighbors. Búsqueda por proximidad en espacio vectorial. |
| **RAG** | Retrieval Augmented Generation. Recuperar info y pasarla al LLM en el prompt. |
| **ReAct** | Reason + Act. Loop de razonamiento y ejecución de tools. |
| **Service ID** | Identidad de servicio en IBM Cloud, para apps (no usuarios). |
| **Similitud coseno** | Métrica para comparar dos vectores, valor entre -1 y 1. |
| **System prompt** | Mensaje inicial que define el comportamiento permanente del modelo. |
| **Token** | Unidad mínima que procesa un LLM (~sílaba o palabra corta). |
| **Tool calling** | Capacidad del modelo de invocar funciones externas. |
| **top-k** | Cantidad de chunks recuperados de la base vectorial por query. |
| **top_p** | Parámetro de sampling complementario a la temperatura. |
| **Enterprise Search** | Capa sobre Elasticsearch con connectors, crawler y Search UI listos para usar. |
| **ELK stack** | Elasticsearch + Logstash + Kibana. El uso "clásico" de Elastic para observabilidad. |
| **Inverted index** | Estructura de índice que mapea palabras → documentos que las contienen. Base de BM25. |
| **Kibana** | Interfaz gráfica oficial sobre Elasticsearch. No tiene lógica propia, solo llama a su API. |
| **Mapping** | Definición de los campos y tipos de un índice en Elasticsearch (como un schema). |

---

## Anexo B — Cheatsheet de troubleshooting

| Error | Causa probable | Cómo resolverlo |
|---|---|---|
| `401 Unauthorized` | API key inválida o vencida | Regenerá la key, revisá espacios al copiar |
| `403 Forbidden` | Falta de permisos en el resource group | Pedir rol al admin del workshop |
| `404 project not found` | `PROJECT_ID` o región incorrecta | Verificar `WX_URL` y proyecto en cloud.ibm.com |
| Modelo "no responde" como esperás | Temperatura alta o prompt ambiguo | Bajar a 0, reformular instrucciones |
| Agente loopea infinitamente | Tool devuelve error y modelo reintenta | Poner max_iterations, mejorar mensaje de error |
| Respuestas inventadas (alucinación) | Falta contexto o instrucción de "no inventes" | Sumar RAG, agregar regla NO_SE en system prompt |
| RAG devuelve resultados irrelevantes | Chunking malo o embedding modelo distinto al index | Re-indexar con mismo modelo, revisar tamaño de chunks |
| Truncado silencioso de output | Excedió max_tokens | Subir `max_new_tokens` o pedir respuesta más corta |
| YAML de Orchestrate no se importa | `spec_version` incorrecta o campo faltante | Validar contra el schema de la versión actual |
| Orquestador no delega al agente esperado | `description` mal redactada | Reescribir la description enfocada en capacidades |

---

## Anexo C — Lecturas recomendadas

- **Prompt engineering techniques** - OReilly - `Solicitar copia`
- **AI Engineering** - OReilly - `Solicitar copia`
- **Agentic Design Patterns** - Springer - `Solicitar copia`
- **Building AI and LLM Applications** - OReilly - `Solicitar copia`
