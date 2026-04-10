
### Test 1 - Request perfecta
``` bash
{
  "service": "Azure Function App",
  "summary": "Plataforma serverless para event-driven workloads",
  "user_context": {
    "tree_path": ["node_start", "node_nano_servicios_check", "deep_functions"],
    "deep_dive_answers": {
      "proposito_uso": "procesar archivos subidos a Blob Storage",
      "ejecucion_constante": "no, event-driven",
      "latencia_arranque": "espero unos 50 mil eventos por día, cada ejecución tarda alrededor de 500ms",
      "trigger_tipo": "Blob Storage",
      "lenguaje": "Python"
    }
  },
  "handoff": {
    "next_agent": "cu-02-cost-estimator",
    "required_inputs": ["expected_requests_per_month", "avg_execution_time_ms", "memory_mb", "trigger_tipo", "plan"],
    "params": { "service": "azure_functions", "pricing_tier": "consumption" }
  }
}
```

### Test 2 - Forzar GAP-Fill
```bash
{
  "service": "Azure Function App",
  "user_context": {
    "tree_path": ["node_start", "deep_functions"],
    "deep_dive_answers": {
      "proposito_uso": "API HTTP para webhooks",
      "latencia_arranque": "no sé bien, tráfico medio nada del otro mundo",
      "trigger_tipo": "HTTP"
    }
  },
  "handoff": {
    "next_agent": "cu-02-cost-estimator",
    "required_inputs": ["expected_requests_per_month", "avg_execution_time_ms", "memory_mb"],
    "params": { "service": "azure_functions", "pricing_tier": "consumption" }
  }
}
```

### Test 3 — Volumen alto, fuera del free tier
```bash
{
  "service": "Azure Function App",
  "user_context": {
    "tree_path": ["node_start", "deep_functions"],
    "deep_dive_answers": {
      "latencia_arranque": "100 millones de ejecuciones por mes, cada una tarda 1 segundo"
    }
  },
  "handoff": {
    "next_agent": "cu-02-cost-estimator",
    "required_inputs": ["expected_requests_per_month", "avg_execution_time_ms", "memory_mb"],
    "params": { "service": "azure_functions", "pricing_tier": "consumption" }
  }
}
```

### Test 4 — Servicio no soportado
```bash
{
  "service": "Azure Kubernetes Service",
  "user_context": {
    "tree_path": ["node_start", "deep_aks"],
    "deep_dive_answers": {
      "ka_nodos": "3 nodos D4s_v3"
    }
  },
  "handoff": {
    "next_agent": "cu-02-cost-estimator",
    "required_inputs": ["node_sku", "node_count"],
    "params": { "service": "aks", "pricing_tier": "pay_as_you_go" }
  }
}
```
