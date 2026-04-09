# Agenda

## Dia 1

### 09:00 - 09:30 | Desayuno

### 09:30 - 10:00 | Intro

- Objetivo
- Foto final
- Reglas, repo, credenciales
- Ronda rapida presentación

### 10:00 - 10:45 | Revision IA: Conceptos generales

- Cómo funciona un LLM: tokens, contexto, temperatura. Diferencia entre modelo base, instruct y chat. Por qué los modelos alucinan y cómo mitigarlo
- Embeddings y búsqueda semántica: qué es un embedding en términos prácticos y por qué importa para el Día 3 (Elastic + Milvus)
- Agentes y herramientas: qué es un agente realmente, el loop razonamiento -> acción -> observación. Tools, function calling y multi-agente
- Prompt engineering práctico: system prompt, user prompt, few-shot. Patrones concretos que van a usar en el mismo día

### 10:45 - 11:00 | IBM Cloud: modelo mental del entorno

- IBM Cloud -> Resource Groups -> Instancias de servicio -> Proyectos
- Watsonx como SaaS: no se instala, se consume vía API
- IAM: cómo funcionan las API keys y los roles
- Terraform: Como se levantó este entorno, así lo replican

### 11:00 - 12:30 | Onboarding Watsonx suite IBM

- Orchestrate: abrir la interfaz, ver un agente de ejemplo precargado, tools y knowledge base
- Watsonx.AI: acceso, crear proyecto, Prompt Lab, primer llamado a API. Todos con una API key funcionando
- Governance: Review de governance, conceptos, uso y demo
- [Opcional] SDK / librería Python: el mismo llamado desde código. (Ejercicio para correr un primer notebook)
- [Opcional] Elasticsearch: conexión, índice de ejemplo, primera búsqueda

### 12:30 - 14:00 | Almuerzo

### 14:00 - 17:00 | Desarrollo agente — Caso de uso 1

---

## Dia 2

### 9:00 - 9:30 | Desayuno

### 9:30 - 10:00 | Repaso

- Revisión de lo construido el Día 1 hecha por devs
- Preguntas abiertas y dudas del agente 1
- Contexto de lo que viene en el día

### 10:00 - 12:30 | Desarrollo agente — Caso de uso 2

### 12:30 - 14:00 | Almuerzo

### 14:00 - 14:30 | Intro Orchestrate

- Qué es Orchestrate y qué lo diferencia de un agente standalone
- Modelo de orquestación: agente coordinador que delega tareas a agentes especializados
- Anatomía de un YAML en Orchestrate: estructura, campos clave, cómo se define un agente
- El ADK: qué expone, cómo se usa para importar modelos externos

### 14:30 - 17:00 | Práctica Orchestrate y ADK + Orquestación de agentes

---

## Dia 3
### 9:00 - 9:30 | Desayuno

### 9:30 - 12:30 | Base de conocimiento (teoria y hands on): Elasticsearch + Milvus / watsonx.data

### 12:30 - 14:00 | Almuerzo

### 14:00 - 16:00 | Ejercicios con IBM BOB

### 

### 16:00 - 16:30 | Recap ecosistema y buenas prácticas

- Cada participante comparte qué construyó y qué se lleva
- Mapa del ecosistema completo: cómo conectan todos los servicios vistos
- Buenas prácticas: prompting en producción, gestión de contexto, patrones de orquestación

### 16:30 - 17:00 | Cierre

- Consultas abiertas
- Próximos pasos dentro del roadmap de adopción
- Recursos y referencias para continuar
