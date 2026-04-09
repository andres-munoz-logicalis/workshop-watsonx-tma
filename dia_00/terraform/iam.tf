# Service ID que usa Code Engine para leer imágenes del Container Registry
resource "ibm_iam_service_id" "ce_service_id" {
  name        = "${var.project_name}-ce-sa"
  description = "Service ID para que Code Engine lea del Container Registry"
  tags        = var.tags
}

resource "ibm_iam_service_policy" "ce_registry_policy" {
  iam_id = ibm_iam_service_id.ce_service_id.id
  roles  = ["Reader", "Writer"]

  resources {
    service = "container-registry"
  }
}

resource "ibm_iam_service_api_key" "ce_api_key" {
  name           = "${var.project_name}-ce-apikey"
  iam_service_id = ibm_iam_service_id.ce_service_id.iam_id
}
