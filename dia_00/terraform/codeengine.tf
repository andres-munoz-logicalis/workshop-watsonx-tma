# Recursos compartidos
resource "random_password" "ent_search_key" {
  length  = 32
  special = false
}

# Proyecto Code Engine
resource "ibm_code_engine_project" "ce_project" {
  name              = "${var.project_name}-ce-project"
  resource_group_id = module.resource_group.resource_group_id
}

# Secrets
resource "ibm_code_engine_secret" "es_credentials" {
  project_id = ibm_code_engine_project.ce_project.project_id
  name       = var.es_secret_name
  format     = "generic"

  data = {
    username = "admin"
    password = var.es_admin_password
  }
}

resource "ibm_code_engine_secret" "registry_secret" {
  project_id = ibm_code_engine_project.ce_project.project_id
  name       = "registry-secret"
  format     = "registry"

  data = {
    username = "iamapikey"
    password = var.ibmcloud_api_key
    server   = local.icr_url
  }
}

resource "ibm_code_engine_secret" "ca_cert" {
  project_id = ibm_code_engine_project.ce_project.project_id
  name       = "es-ca-cert"
  format     = "generic"

  data = {
    "ca.crt" = base64decode(data.ibm_database_connection.es_connection.https[0].certificate[0].certificate_base64)
  }
}

# Kibana
resource "ibm_code_engine_app" "kibana_app" {
  project_id      = ibm_code_engine_project.ce_project.project_id
  name            = var.kibana_app_name
  image_reference = "docker.elastic.co/kibana/kibana:${local.es_full_version}"
  image_port      = 5601

  scale_min_instances = var.min_instances
  scale_max_instances = var.max_instances

  run_env_variables {
    type      = "secret_key_reference"
    name      = "ELASTICSEARCH_USERNAME"
    reference = ibm_code_engine_secret.es_credentials.name
    key       = "username"
  }
  run_env_variables {
    type      = "secret_key_reference"
    name      = "ELASTICSEARCH_PASSWORD"
    reference = ibm_code_engine_secret.es_credentials.name
    key       = "password"
  }
  run_env_variables {
    type  = "literal"
    name  = "ENTERPRISESEARCH_HOST"
    value = local.ent_search_cluster_url
  }

  dynamic "run_env_variables" {
    for_each = local.kibana_env
    content {
      type  = "literal"
      name  = run_env_variables.key
      value = run_env_variables.value
    }
  }

  run_volume_mounts {
    type       = "secret"
    mount_path = "/tmp/certs"
    reference  = ibm_code_engine_secret.ca_cert.name
  }
}

# Enterprise Search
resource "ibm_code_engine_app" "ent_search_app" {
  project_id      = ibm_code_engine_project.ce_project.project_id
  name            = "enterprise-search"
  image_reference = "docker.elastic.co/enterprise-search/enterprise-search:${local.es_full_version}"
  image_port      = 3002

  scale_min_instances = var.min_instances
  scale_max_instances = var.max_instances

  timeouts {
    create = "10m"
    update = "10m"
  }

  dynamic "run_env_variables" {
    for_each = local.ent_search_env
    content {
      type  = "literal"
      name  = run_env_variables.key
      value = run_env_variables.value
    }
  }
  run_env_variables {
    type  = "literal"
    name  = "kibana.external_url"
    value = local.kibana_url
  }
  run_env_variables {
    type  = "literal"
    name  = "kibana.host"
    value = local.kibana_url
  }

  run_volume_mounts {
    type       = "secret"
    mount_path = "/tmp/certs"
    reference  = ibm_code_engine_secret.ca_cert.name
  }
}


# API Decision Tree
resource "ibm_code_engine_app" "api_decision_tree" {
  project_id      = ibm_code_engine_project.ce_project.project_id
  name            = var.decision_tree_app_name
  image_reference = "${local.icr_url}/${module.container_registry.namespace_name}/${var.decision_tree_image_name}:latest"
  image_secret    = ibm_code_engine_secret.registry_secret.name
  image_port      = 8080

  scale_min_instances = var.min_instances
  scale_max_instances = var.max_instances

  run_env_variables {
    type  = "literal"
    name  = "CLOUDANT_URL"
    value = ibm_resource_key.cloudant_credentials.credentials["url"]
  }

  run_env_variables {
    type  = "literal"
    name  = "CLOUDANT_APIKEY"
    value = ibm_resource_key.cloudant_credentials.credentials["apikey"]
  }

  run_env_variables {
    type  = "literal"
    name  = "CLOUDANT_DB"
    value = var.decision_tree_db_name
  }

  run_env_variables {
    type  = "literal"
    name  = "API_PUBLIC_URL"
    value = "https://${var.decision_tree_app_name}.${var.ce_subdomain}.us-south.codeengine.appdomain.cloud"
  }

  run_env_variables {
    type  = "literal"
    name  = "MATCH_THRESHOLD"
    value = "0.5"
  }

}

resource "ibm_code_engine_app" "api_azure_pricing" {
  project_id      = ibm_code_engine_project.ce_project.project_id
  name            = var.azure_pricing_app_name
  image_reference = "${local.icr_url}/${module.container_registry.namespace_name}/${var.azure_pricing_image_name}:latest"
  image_secret    = ibm_code_engine_secret.registry_secret.name
  image_port      = 8080

  scale_min_instances = var.min_instances
  scale_max_instances = var.max_instances

  run_env_variables {
    type  = "literal"
    name  = "API_PUBLIC_URL"
    value = "https://${var.azure_pricing_app_name}.${var.ce_subdomain}.us-south.codeengine.appdomain.cloud"
  }
}

/*
# Python App
resource "ibm_code_engine_app" "python_app" {
  project_id = ibm_code_engine_project.ce_project.project_id
  name       = "python-bot-app"

  image_reference = "${local.icr_url}/${module.container_registry.namespace_name}/pythonapp:latest"
  image_secret    = ibm_code_engine_secret.registry_secret.name
  image_port      = 8080

  scale_min_instances = var.min_instances
  scale_max_instances = var.max_instances

  dynamic "run_env_variables" {
    for_each = local.python_app_env
    content {
      type  = "literal"
      name  = run_env_variables.key
      value = run_env_variables.value
    }
  }

  run_volume_mounts {
    type       = "secret"
    mount_path = "/tmp/certs"
    reference  = ibm_code_engine_secret.ca_cert.name
  }
}
*/
