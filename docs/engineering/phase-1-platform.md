# Phase 1: platform foundation

## What was built
- Terraform (infra/): kind cluster, three namespaces (gateway, observability, compliance), Argo CD via Helm, and a bootstrap chart that creates the root application.
- GitOps (deploy/): root app of apps, a Helm chart (hello) deployed as dev and prod, Kyverno and one policy.

## Tested
- Full destroy and rebuild with one terraform apply. All five applications returned to Synced and Healthy.
- A root container (nginx) was rejected in hello-dev. A non-root pod started normally.
- Changing replicas in Git changed the cluster. Scaling by hand was reverted by Argo CD self-heal.

## Decisions
- Chart and provider versions are pinned so a rebuild gives the same result.
- The root app is created by a small Helm chart, because Terraform cannot create an Argo CD resource in the same run that installs Argo CD.
- The policy uses Kyverno ValidatingPolicy. ClusterPolicy is deprecated in Kyverno 1.19 and due for removal in 1.20.
- The policy is limited to the two sample namespaces so it cannot block system pods.

## Problems I hit
- Kyverno showed OutOfSync because its CRDs differ by empty labels and annotations. Fixed with the ServerSideDiff compare option.

## Known limits
- Single-node local cluster, Apple-silicon Mac only. No CI yet.
- The policy checks containers only, not init containers, and covers two namespaces.
- No image signing yet (planned for the CI phase).