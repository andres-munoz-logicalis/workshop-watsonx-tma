terraform {
  required_providers {
    ibm = {
      source  = "IBM-Cloud/ibm"
      version = ">= 1.89.0, < 2.0.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
    http = {
      source  = "hashicorp/http"
      version = "~> 3.4"
    }
    restapi = {
      source  = "mastercard/restapi"
      version = ">= 2.0.1, < 3.0.0"
    }
  }

  backend "s3" {
    bucket   = "cos-state-iac"
    key      = "workshop/terraform.tfstate"
    region   = "us-south"
    endpoint = "https://s3.us-south.cloud-object-storage.appdomain.cloud"

    skip_region_validation      = true
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_requesting_account_id  = true
    skip_s3_checksum            = true
  }
}

provider "ibm" {
  ibmcloud_api_key = var.ibmcloud_api_key
  region           = var.region
}

data "ibm_iam_auth_token" "restapi" {
}

provider "restapi" {
  uri                  = "https:"
  write_returns_object = true
  debug                = true
  headers = {
    Authorization = data.ibm_iam_auth_token.restapi.iam_access_token
    Content-Type  = "application/json"
  }
}
