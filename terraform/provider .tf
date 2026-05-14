terraform {
  required_version = "1.15.2"
  required_providers {
    genesyscloud = {
      source  = "mypurecloud/genesyscloud"
      version = ">= 1.6.0"
    }
  }
  cloud {
    organization = "Itapiruba"
    workspaces {
      name = "Solve"
    }
  }
}

variable "genesys_region" {
  type    = string
  default = "sa-east-1"
}

provider "genesyscloud" {
  aws_region = var.genesys_region
  # O ID e Secret ele pegará das env vars silenciosamente.
}
