# General
variable "ibmcloud_api_key" {
  type      = string
  sensitive = true
}

variable "region" {
  type    = string
  default = "us-south"
}

variable "tags" {
  type        = list(string)
  description = "Tags aplicados a todos los recursos"
  default     = []
}

variable "resource_group_name" {
  type        = string
  description = "Nombre del nuevo Resource Group que Terraform va a crear para toda la infra"
}

variable "project_name" {
  type        = string
  default     = "workshop"
  description = "Prefijo usado para nombrar todos los recursos"
}

# Elasticsearch
variable "es_admin_password" {
  type        = string
  sensitive   = true
  description = "Password del usuario admin de Elasticsearch"
}

variable "es_username_created_01" {
  type        = string
  sensitive   = true
  description = "Nombre del usuario adicional creado en Elasticsearch"
}

variable "es_password_created_01" {
  type        = string
  sensitive   = true
  description = "Password del usuario adicional de Elasticsearch"
}

variable "es_ssl_verification_mode" {
  type    = string
  default = "none"
}

# Cloudant
variable "cloudant_instance_name" {
  type    = string
  default = "cloudant"
}

variable "cloudant_plan" {
  type    = string
  default = "standard"
}

# watsonx.ai 
variable "watsonx_ai_studio_plan" {
  type    = string
  default = "professional-v1"
}

variable "watsonx_ai_runtime_plan" {
  type    = string
  default = "v2-standard"
}

variable "watsonx_ai_project_name" {
  type    = string
  default = "workshop-project"
}

variable "watsonx_ai_studio_name" {
  type    = string
  default = "watsonx-ai-studio"
}

variable "watsonx_ai_runtime_name" {
  type    = string
  default = "watsonx-ai-studio"
}

# watsonx.data

variable "watsonx_data_name" {
  type    = string
  default = "watsonx-data"
}

variable "watsonx_data_plan" {
  type    = string
  default = "lakehouse-enterprise"
}

# watsonx Orchestrate

variable "watsonx_orchestrate_name" {
  type    = string
  default = "watsonx-orchestrate"
}

variable "watsonx_orchestrate_plan" {
  type    = string
  default = "standard-agentic-mau"
}

# Code Engine

variable "ce_subdomain" {
  type        = string
  description = "Subdomain del CE project. Se obtiene después del primer apply. Ej: 28fzvauz0vhk"
  default     = ""
}

variable "kibana_app_name" {
  type    = string
  default = "kibana"
}

variable "es_secret_name" {
  type    = string
  default = "es-credentials"
}

variable "min_instances" {
  type    = number
  default = 1
}

variable "max_instances" {
  type    = number
  default = 1
}

variable "watsonx_project_id" {
  type        = string
  description = "ID del proyecto watsonx.ai (usado por la Python app)"
}

variable "es_python_app_index" {
  type        = string
  description = "Index pyton app"
  default     = "indice-prueba"
}

variable "decision_tree_app_name" {
  type    = string
  default = "api-decision-tree"
}

variable "decision_tree_image_name" {
  type    = string
  default = "api-decision-tree"
}

variable "decision_tree_db_name" {
  type    = string
  default = "decision_tree"
}

variable "azure_pricing_app_name" {
  type    = string
  default = "api-azure-pricing"
}

variable "azure_pricing_image_name" {
  type    = string
  default = "api-azure-pricing"
}
