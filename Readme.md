# Agenda

## Dia 1

### 09:00 - 09:30 | Desayuno

### 09:30 - 9:45 | Intro

- Ronda rapida presentación
- Armado de grupos, credenciales y repo

### 9:45 - 10:15 | Revision IA: Conceptos generales

- Cómo funciona un LLM: tokens, contexto, temperatura. Diferencia entre modelo base, instruct y chat. Por qué los modelos alucinan y cómo mitigarlo
- Agentes y herramientas: qué es un agente realmente, el loop razonamiento -> acción -> observación. Tools, function calling y multi-agente
- Prompt engineering práctico: system prompt, user prompt, few-shot. Patrones concretos que van a usar en el mismo día
- Embeddings y búsqueda semántica: qué es un embedding en términos prácticos y por qué importa

### 10:15 - 10:30 | IBM Cloud: modelo mental del entorno

- IBM Cloud -> Resource Groups -> Instancias de servicio -> Proyectos
- Watsonx como SaaS: no se instala, se consume vía API
- IAM: cómo funcionan las API keys y los roles
- Terraform: Como se levantó este entorno

### 10:30 - 11:00 | Onboarding Watsonx suite IBM

- Orchestrate: abrir la interfaz, ver un agente de ejemplo precargado, tools y knowledge base
- Governance: Review de governance, conceptos, uso y demo
- [Opcional] Watsonx.AI: acceso, crear proyecto, Prompt Lab, primer llamado a API. Todos con una API key funcionando
- [Opcional] SDK / librería Python: el mismo llamado desde código. (Ejercicio para correr un primer notebook)
- [Opcional] Elasticsearch: conexión, índice de ejemplo, primera búsqueda

### 11:00 - 12:30 | Hands On Agente 1
- Diseño de agente en equipo y feedback [30 min]
- Planteo y desarrollo de tools [60 min]


### 12:30 - 14:00 | Almuerzo

### 14:00 en adelante | Hands On Agente 1 (Continuación)
- Desarrollo de agente en Orchestrate [1h]
- Review agente y tools ya desarrollado

---

## Dia 2

### 9:00 - 9:30 | Desayuno

### 9:30 - 10:00 | Repaso

- Revisión de lo construido y aprendido por grupo (mini exposición)
- Preguntas abiertas y dudas del agente 1

### 10:00 - 12:30 | Hands On Agente 2
- Diseño de agente en equipo y feedback [30 min]
- Planteo y desarrollo de tools [60 min]
- Review agente y tools ya desarrollado [30 min]

### 12:30 - 14:00 | Almuerzo

### 14:00 - 14:15 | Orquestación de agentes

- Modelo de orquestación: agente coordinador que delega tareas a agentes especializados
- Anatomía de un YAML en Orchestrate: estructura, campos clave, cómo se define un agente
- El ADK: qué expone, cómo se usa para importar modelos externos

### 14:15 en adelante | Hands On práctica Orchestrate ADK + Orquestación de agentes

---

## Dia 3
### 9:00 - 9:30 | Desayuno

### 9:30 - 10:00 | Governance

### 10:00 - 11:00 | Base de conocimientos con Elasticsearch 
- Teoria y repaso de capacidades Elastic, Enterpise search, Kibana, base de conocimiento, RAG [30 min]
- Hands on ejercicios [30 min]

### 11:00 - 11:30 | Recap ecosistema y buenas prácticas

- Cada participante comparte qué construyó y qué se lleva
- Mapa del ecosistema completo: cómo conectan todos los servicios vistos
- Buenas prácticas: prompting en producción, gestión de contexto, patrones de orquestación

### 12:00 - 12:30 | Cierre

- Consultas abiertas
- Próximos pasos dentro del roadmap de adopción
- Recursos y referencias para continuar

### 13:00 - 14:00 | Almuerzo

### 14:00 en adelante | Espacio opcional para review

- Revisión de conceptos y uso de la herramienta
- Posibilidad de terminar agentes del dia 1 y 2
- Mejora del flujo agentico
- Revisión de agentes ya desarrollados
- Revisión ejercicios RAG
- Deep dive arquitectura e IaC usada
