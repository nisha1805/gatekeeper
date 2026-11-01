provider "kind" {}

resource "kind_cluster" "gatekeeper" {
  name            = "gatekeeper"
  wait_for_ready  = true
  kubeconfig_path = "${path.module}/gatekeeper.kubeconfig"

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"
    }
  }
}