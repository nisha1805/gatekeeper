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

provider "kubernetes" {
  host                   = kind_cluster.gatekeeper.endpoint
  client_certificate     = kind_cluster.gatekeeper.client_certificate
  client_key             = kind_cluster.gatekeeper.client_key
  cluster_ca_certificate = kind_cluster.gatekeeper.cluster_ca_certificate
}

locals {
  namespaces = ["gateway", "observability", "compliance"]
}

resource "kubernetes_namespace" "app" {
  for_each = toset(local.namespaces)

  metadata {
    name = each.key
  }
}