# Gatekeeper

An AI gateway with EU AI Act compliance workflows, built as a hands-on portfolio project.

**Status: work in progress. Prototype only, no real users.** Nothing here is production-ready.

## The problem

When several teams add AI features, three things get out of control: cost (nobody knows what an answer costs), quality (prompts and models change without measurement) and compliance (EU AI Act duties need classification and evidence). See [the problem brief](docs/product/problem-brief.md).

## What works today

**Platform (Phase 1)**
- One `terraform apply` builds a local Kubernetes cluster (kind), creates namespaces and installs Argo CD.
- Argo CD watches this repo (app of apps). A change pushed to `deploy/` reaches the cluster without running `kubectl`.
- A sample app is packaged as a Helm chart and deployed twice: dev (1 replica) and prod (2 replicas).
- A Kyverno policy reje- A Kyverno policy rejects containers that do not set `runAsNonRoot`, in the sample namespaces and in the gateway namespace.
- I tested a full destroy and rebuild: all applications and the policy came back from Git on their own.

**Gateway (Phase 2, in progress)**
- LiteLLM runs in the cluster with its own Postgres, deployed through Argo CD with pinned versions.
- Two models sit behind one door: `chat-primary` (Claude Haiku) and `chat-backup` (Claude Sonnet). If the primary fails, the gateway retries once and then falls back to the backup.
- I tested the fallback with an outage drill: I broke the primary through a Git commit, a request still returned an answer from the backup, and `git revert` repaired it.
- Two teams each have their own virtual key and budget. In a test, a team with a tiny budget was blocked after a few requests while the other team kept working. Enforcement overshot the limit by about 18 percent, so budgets are a guard rail, not an exact limit.
- `scripts/smoke-test.sh` checks the whole gateway in one command (6 checks, all passing on a fresh rebuild).
- API keys never enter Git. They live in git-ignored local files, and a script loads them into the cluster.
- The gateway (official non-root LiteLLM image) and Postgres run as non-root users, and the policy above refuses a root container in the gateway namespace. I checked this against the running cluster, not only against Git.

## What is not built yet

Observability and SLOs, the evaluation gate in CI, the compliance module, guardrails and the product documents. Each is planned and will be listed above only once it works.

## Quick start

You need Docker Desktop (running, with about 5 GiB of memory), Terraform, kubectl, Helm and an Anthropic API key. Put your own key in a local `.env` file (see `scripts/create-secrets.sh` for the names it reads).

```
git clone https://github.com/nisha1805/gatekeeper.git
cd gatekeeper/infra
terraform init
terraform apply
cd ..
export KUBECONFIG="$PWD/infra/gatekeeper.kubeconfig"
./scripts/create-secrets.sh
kubectl -n argocd get applications
```

The first run takes 5 to 10 minutes. Then, with `kubectl -n gateway port-forward svc/litellm 4000:4000` running in another window:

```
./scripts/seed-teams.sh
./scripts/smoke-test.sh
```

Tested on an Apple-silicon Mac with 8 GB of memory only. On a machine that size, close other heavy apps while the cluster runs.

## Inspired by and built on

Tools I use, and what for. Licences will be checked and listed here before the project is published.

- LiteLLM: the gateway (keys, budgets, routing, fallback). I configure and test it. I did not write it.
- Anthropic Claude models, through the API
- Argo CD: GitOps delivery
- kind and the tehcyx kind Terraform provider: local cluster
- Terraform, Helm: infrastructure and packaging
- Kyverno: policy as code
- PostgreSQL: the gateway's database
- gitleaks: scans commits for secrets

## Honesty notes

- Public and synthetic data only. Nothing from any employer.
- This is decision support, not legal advice.
- I will only claim what I have built, and only report numbers I can reproduce.

## Licence

MIT. See [LICENSE](LICENSE).