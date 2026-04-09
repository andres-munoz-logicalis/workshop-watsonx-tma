# COS
resource "ibm_resource_instance" "watsonx_cos" {
  name              = "${var.project_name}-watsonx-cos"
  resource_group_id = module.resource_group.resource_group_id
  service           = "cloud-object-storage"
  plan              = "standard"
  location          = "global" # COS siempre es global en IBM Cloud
  tags              = var.tags
}

# watsonx.ai
module "watsonx_ai" {
  source  = "terraform-ibm-modules/watsonx-ai/ibm"
  version = "~> 2.16"
  region  = var.region

  resource_group_id                = module.resource_group.resource_group_id
  watsonx_ai_studio_instance_name  = "${var.project_name}-${var.watsonx_ai_studio_name}"
  watsonx_ai_runtime_instance_name = "${var.project_name}-${var.watsonx_ai_runtime_name}"
  watsonx_ai_studio_plan           = var.watsonx_ai_studio_plan
  watsonx_ai_runtime_plan          = var.watsonx_ai_runtime_plan

  cos_instance_crn = ibm_resource_instance.watsonx_cos.crn

  project_name = var.watsonx_ai_project_name

  resource_tags = var.tags
}

# watsonx.data
module "watsonx_data" {
  source  = "terraform-ibm-modules/watsonx-data/ibm"
  version = "~> 1.15"

  watsonx_data_name = "${var.project_name}-${var.watsonx_data_name}"
  region            = var.region
  resource_group_id = module.resource_group.resource_group_id
  plan              = var.watsonx_data_plan
  resource_tags     = var.tags
}

# watsonx Orchestrate
module "watsonx_orchestrate" {
  source  = "terraform-ibm-modules/watsonx-orchestrate/ibm"
  version = "~> 1.3"

  region                   = var.region
  resource_group_id        = module.resource_group.resource_group_id
  watsonx_orchestrate_name = "${var.project_name}-${var.watsonx_orchestrate_name}"
  plan                     = var.watsonx_orchestrate_plan
  resource_tags            = var.tags
}
