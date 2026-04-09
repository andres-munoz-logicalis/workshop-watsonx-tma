module "cloudant" {
  source  = "terraform-ibm-modules/cloudant/ibm"
  version = "~> 1.5"

  instance_name     = "${var.project_name}-${var.cloudant_instance_name}"
  resource_group_id = module.resource_group.resource_group_id
  region            = var.region
  plan              = var.cloudant_plan

  capacity = 1

  tags = var.tags
}

# Credencial de servicio para acceder a Cloudant desde aplicaciones
resource "ibm_resource_key" "cloudant_credentials" {
  name                 = "${var.project_name}-cloudant-credentials"
  role                 = "Manager"
  resource_instance_id = module.cloudant.instance_id
  tags                 = var.tags
}
