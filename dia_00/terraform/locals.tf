# Container Registry
locals {
  region_to_icr = {
    "us-south" = "us.icr.io"
    "us-east"  = "us.icr.io"
    "eu-gb"    = "uk.icr.io"
    "eu-de"    = "eu.icr.io"
    "jp-tok"   = "jp.icr.io"
    "jp-osa"   = "jp.icr.io"
    "au-syd"   = "au.icr.io"
    "ca-tor"   = "ca.icr.io"
    "br-sao"   = "br.icr.io"
  }
  icr_url = lookup(local.region_to_icr, var.region, "us.icr.io")
}

# Elasticsearch
locals {
  es_host = data.ibm_database_connection.es_connection.https[0].hosts[0].hostname
  es_port = data.ibm_database_connection.es_connection.https[0].hosts[0].port

  es_metadata     = jsondecode(data.http.es_metadata.response_body)
  es_full_version = local.es_metadata.version.number
}

# Code Engine — URLs internas
locals {
  kibana_url             = "https://${var.kibana_app_name}.${var.ce_subdomain}.us-south.codeengine.appdomain.cloud"
  ent_search_url         = "https://enterprise-search.${var.ce_subdomain}.us-south.codeengine.appdomain.cloud"
  kibana_cluster_url     = "http://${var.kibana_app_name}.${var.ce_subdomain}.svc.cluster.local"
  ent_search_cluster_url = "http://enterprise-search.${var.ce_subdomain}.svc.cluster.local"
}


# Code Engine
locals {
  kibana_env = {
    ELASTICSEARCH_HOSTS                       = "[\"https://${local.es_host}:${local.es_port}\"]"
    ELASTICSEARCH_SSL_ENABLED                 = "true"
    ELASTICSEARCH_SSL_VERIFICATIONMODE        = var.es_ssl_verification_mode
    SERVER_HOST                               = "0.0.0.0"
    ELASTICSEARCH_SSL_CERTIFICATEAUTHORITIES  = "/tmp/certs/ca.crt"
    XPACK_SECURITY_ENCRYPTIONKEY              = random_password.ent_search_key.result
    XPACK_ENCRYPTEDSAVEDOBJECTS_ENCRYPTIONKEY = random_password.ent_search_key.result
    XPACK_REPORTING_ENCRYPTIONKEY             = random_password.ent_search_key.result
    ENTERPRISESEARCH_SSL_VERIFICATIONMODE     = "none"
    NODE_TLS_REJECT_UNAUTHORIZED              = "0"
    SERVER_PUBLICBASEURL                      = local.kibana_url # ← disponible porque viene de var
  }

  ent_search_env = {
    "elasticsearch.host"                      = "https://${local.es_host}:${local.es_port}"
    "elasticsearch.username"                  = "admin"
    "elasticsearch.password"                  = var.es_admin_password
    "allow_es_sig_requests"                   = "true"
    "allow_es_settings_modification"          = "true"
    "ENT_SEARCH_DEFAULT_PASSWORD"             = var.es_admin_password
    "secret_management.encryption_keys"       = "[${random_password.ent_search_key.result}]"
    "elasticsearch.ssl.enabled"               = "true"
    "elasticsearch.ssl.certificate_authority" = "/tmp/certs/ca.crt"
    "SSL_CERT_FILE"                           = "/tmp/certs/ca.crt"
    "kibana.startup_retry.enabled"            = "true"
    "kibana.startup_retry.fail_after"         = "60"
    "ent_search.external_url"                 = local.ent_search_url
    "ent_search.listen_host"                  = "0.0.0.0"
    "ent_search.listen_port"                  = "3002"
  }

  python_app_env = {
    "ELASTIC_HOST"     = "https://${local.es_host}:${local.es_port}"
    "ELASTIC_USERNAME" = var.es_username_created_01
    "ELASTIC_PASSWORD" = var.es_password_created_01
    "ELASTIC_INDEX"    = var.es_python_app_index
    "PROJECT_ID"       = var.watsonx_project_id
    "API_KEY"          = var.ibmcloud_api_key
    "API_URL"          = "https://us-south.ml.cloud.ibm.com"
    "FORCE_RESTART"    = "20"
  }
}
