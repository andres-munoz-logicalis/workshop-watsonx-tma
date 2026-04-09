# Resource Group
output "resource_group_id" {
  description = "ID del Resource Group del ambiente"
  value       = module.resource_group.resource_group_id
}

# Container Registry
output "registry_base_url" {
  description = "URL base para docker push. Ej: docker push <url>/imagen:tag"
  value       = "${local.icr_url}/${module.container_registry.namespace_name}"
}

# Elasticsearch
output "es_url" {
  description = "URL completa de conexión a Elasticsearch (incluye credenciales)"
  value       = "https://admin:${var.es_admin_password}@${local.es_host}:${local.es_port}"
  sensitive   = true
}

output "es_host" {
  description = "Hostname de Elasticsearch"
  value       = local.es_host
}

output "es_version" {
  description = "Versión exacta de Elasticsearch desplegada"
  value       = local.es_full_version
}

# Cloudant
output "cloudant_url" {
  description = "URL del endpoint de Cloudant"
  value       = module.cloudant.instance_url
}

output "cloudant_credentials" {
  description = "Credenciales de la service key de Cloudant"
  value       = ibm_resource_key.cloudant_credentials.credentials
  sensitive   = true
}

# watsonx
output "watsonx_ai_project_id" {
  description = "ID del proyecto watsonx.ai creado"
  value       = module.watsonx_ai.watsonx_ai_project_id
}

output "watsonx_ai_studio_crn" {
  description = "CRN de la instancia Watson Studio"
  value       = module.watsonx_ai.watsonx_ai_studio_crn
}

output "watsonx_data_crn" {
  description = "CRN de la instancia watsonx.data"
  value       = module.watsonx_data.crn
}

output "watsonx_orchestrate_crn" {
  description = "CRN de la instancia watsonx Orchestrate"
  value       = module.watsonx_orchestrate.crn
}

# Code Engine

output "kibana_endpoint" {
  description = "URL pública de Kibana"
  value       = ibm_code_engine_app.kibana_app.endpoint
}

output "ent_search_endpoint" {
  description = "URL pública de Enterprise Search"
  value       = ibm_code_engine_app.ent_search_app.endpoint
}

output "decision_tree_endpoint" {
  description = "URL pública de la API Decision Tree"
  value       = ibm_code_engine_app.api_decision_tree.endpoint
}

output "azure_pricing_endpoint" {
  description = "URL pública de la API Azure Pricing"
  value       = ibm_code_engine_app.api_azure_pricing.endpoint
}

/*
output "python_app_endpoint" {
  description = "URL pública del Python Bot"
  value       = ibm_code_engine_app.python_app.endpoint
}
*/
