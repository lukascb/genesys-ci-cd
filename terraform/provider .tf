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

provider "genesyscloud" {
  # O ID e Secret ele pegará das env vars silenciosamente.
  timeouts {
      create = "10m"
      update = "10m"
      delete = "10m"
    }
}
