terraform {
  required_version = "1.15.3"
  required_providers {
    genesyscloud = {
      source  = "mypurecloud/genesyscloud"
      version = ">= 1.6.0"ddd
    }
  }

provider "genesyscloud" {
  # O ID e Secret ele pegará das env vars silenciosamente.
}
