# Gatekeeper

An AI gateway with EU AI Act compliance workflows, built as a hands-on portfolio project.

**Status: work in progress. Prototype only, no real users.** Nothing here is production-ready.

## The problem

When several teams add AI features, three things get out of control: cost (nobody knows what an answer costs), quality (prompts and models change without measurement) and compliance (EU AI Act duties need classification and evidence). See [the problem brief](docs/product/problem-brief.md).

## What works today (Phase 1: platform foundation)

- One `terraform apply` builds a local Kubernetes cluster (kind), creates namespaces and installs Argo CD.
- Argo CD watches this repo (app of apps). A change pushed to `deploy/` reaches the cluster without running `kubectl`.
- A sample app is packaged as a Helm chart and deployed twice: dev (1 replica) and prod (2 replicas).
- A Kyverno policy rejects containers that do not set `runAsNonRoot` in the sample namespaces.
- I tested a full destroy and rebuild: after `terraform destroy` and a new `terraform apply`, all applications and the policy came back from Git on their own.

## What is not built yet

The gateway, observability, the evaluation gate in CI, the compliance module and the product documents. Each is planned and will be listed above only once it works.

## Quick start

You need Docker Desktop (running), Terraform, kubectl and Helm.

```
git clone https://github.com/nisha1805/gatekeeper.git
cd gatekeeper/infra
terraform init
terraform apply
export KUBECONFIG="$PWD/gatekeeper.kubeconfig"
kubectl -n argocd get applications
```

The first run takes about 5 to 8 minutes. Tested on an Apple-silicon Mac only.

## Inspired by and built on

Tools I use, and what for. Licences will be checked and listed here before the project is published.

- Argo CD: GitOps delivery
- kind and the tehcyx kind Terraform provider: local cluster
- Terraform, Helm: infrastructure and packaging
- Kyverno: policy as code

## Honesty notes

- Public and synthetic data only. Nothing from any employer.
- This is decision support, not legal advice.
- I will only claim what I have built, and only report numbers I can reproduce.

## Licence

MIT. See [LICENSE](LICENSE).