resource "genesyscloud_tf_export" "Teste" {
  directory                          = "./genesyscloud/flows"
  export_format                      = "hcl"dddd
  include_filter_resources           = ["genesyscloud_flow::TESTE"]
  use_legacy_architect_flow_exporter = false
}
