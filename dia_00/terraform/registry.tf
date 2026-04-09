module "container_registry" {
  source  = "terraform-ibm-modules/container-registry/ibm"
  version = "~> 2.6"

  namespace_name    = "${var.project_name}-registry"
  resource_group_id = module.resource_group.resource_group_id

  images_per_repo = 3

  tags = var.tags
}
