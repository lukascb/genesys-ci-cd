resource "genesyscloud_tf_export" "Teste" {
  directory                          = "./genesyscloud/flows"jj
  export_format                      = "hcl"
  include_filter_resources           = ["genesyscloud_flow::TESTE"]
  use_legacy_architect_flow_exporter = false
}
