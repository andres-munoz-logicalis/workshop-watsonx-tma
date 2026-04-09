module "elasticsearch" {
  source  = "terraform-ibm-modules/icd-elasticsearch/ibm"
  version = "~> 2.12"

  name              = "${var.project_name}-elastic-db"
  resource_group_id = module.resource_group.resource_group_id
  region            = var.region
  plan              = "platinum"
  service_endpoints = "public-and-private"

  # Credenciales, usurio admin se crea por defecto agregar mas al []
  admin_pass = var.es_admin_password
  users = [
    {
      name     = var.es_username_created_01
      password = var.es_password_created_01
      type     = "database"
    }
  ]

  members   = 3
  memory_mb = 15360
  disk_mb   = 102400
  cpu_count = 3

  use_ibm_owned_encryption_key = true

  deletion_protection = false

  tags = var.tags
}

# Obtener detalles de conexión (host, port, certificado)
data "ibm_database_connection" "es_connection" {
  endpoint_type = "public"
  deployment_id = module.elasticsearch.id
  user_id       = var.es_username_created_01
  user_type     = "database"
}

# Consultar la versión exacta desplegada para usarla en las imágenes Docker
data "http" "es_metadata" {
  url      = "https://admin:${var.es_admin_password}@${local.es_host}:${local.es_port}"
  insecure = true

  depends_on = [module.elasticsearch]
}
