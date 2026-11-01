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

provider "helm" {
  kubernetes {
    host                   = kind_cluster.gatekeeper.endpoint
    client_certificate     = kind_cluster.gatekeeper.client_certificate
    client_key             = kind_cluster.gatekeeper.client_key
    cluster_ca_certificate = kind_cluster.gatekeeper.cluster_ca_certificate
  }
}

resource "helm_release" "argocd" {
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = "10.11.6"
  namespace        = "argocd"
  create_namespace = true
  wait             = true
  timeout          = 600

  # Keep it light for a laptop: we don't need single sign-on or notifications.
  set {
    name  = "dex.enabled"
    value = "false"
  }
  set {
    name  = "notifications.enabled"
    value = "false"
  }
}

resource "helm_release" "bootstrap" {
  name       = "bootstrap"
  chart      = "${path.module}/../deploy/bootstrap"
  namespace  = "argocd"
  depends_on = [helm_release.argocd]
}