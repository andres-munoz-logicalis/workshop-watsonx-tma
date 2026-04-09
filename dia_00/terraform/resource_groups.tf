module "resource_group" {
  source              = "terraform-ibm-modules/resource-group/ibm"
  version             = "1.6.0"
  resource_group_name = var.resource_group_name
}
