# Gatekeeper
[![CI](https://github.com/nisha1805/gatekeeper/actions/workflows/ci.yml/badge.svg)](https://github.com/nisha1805/gatekeeper/actions/workflows/ci.yml)

An AI gateway with EU AI Act compliance workflows, built as a hands-on portfolio project.

**Status: work in progress. Prototype only, no real users.** Nothing here is production-ready.

## The problem

When several teams add AI features, three things get out of control: cost (nobody knows what an answer costs), quality (prompts and models change without measurement) and compliance (EU AI Act duties need classification and evidence). See [the problem brief](docs/product/problem-brief.md).

## What works today

**Platform**
- One `terraform apply` builds a local Kubernetes cluster (kind), creates namespaces and installs Argo CD. Argo CD watches this repo, so a change pushed to `deploy/` reaches the cluster without running `kubectl`.
- A sample app is packaged as a Helm chart and deployed twice: dev (1 replica) and prod (2 replicas).
- A Kyverno policy rejects containers that do not run as non-root, in the sample namespaces and in the gateway namespace.
- I tested a full destroy and rebuild: all applications and the policy came back from Git on their own.

**Gateway**
- LiteLLM runs in the cluster with its own Postgres, delivered through Argo CD with pinned versions, and runs as a non-root user.
- Two models sit behind one door: `chat-primary` (Claude Haiku) and `chat-backup` (Claude Sonnet). If the primary fails, the gateway retries once and then falls back.
- Each team has its own virtual key and budget. In a test, a team with a tiny budget was blocked after a few requests while another team kept working. Enforcement overshot by about 18 percent, so budgets are a guard rail, not an exact limit.
- `scripts/smoke-test.sh` checks the whole gateway in one command.
- API keys never enter Git. They live in git-ignored local files, and a script loads them into the cluster.

**Pipeline**
- GitHub Actions runs five jobs on every push: a gitleaks scan of the full history, Terraform format and validate, Helm lint for both charts, the API tests (83) against a throwaway Postgres, and the UI tests (10).
- Third-party actions are avoided. The only one used is GitHub's own checkout, pinned to an exact commit, and tools are installed at pinned versions. Trivy is not added yet: I want to install a pinned, checksum-verified release rather than trust a version tag.

**Monitoring**
- The gateway exposes Prometheus metrics on a dedicated in-cluster port. A small Prometheus scrapes them, and Grafana shows a dashboard that is provisioned from Git.
- A written service level objective (99% of eligible chat requests succeed) with three alerts: success rate, metrics target down, and backup model in use.
- I tested the alerts with real failures: a pod kill (recovery in about 45 seconds), a broken primary model (the fallback alert fired and cleared), and both models broken. The last drill found a bug in my success-rate rule, which I fixed. The fix was checked by replaying recorded data, not yet by firing live. See [the SLO notes](docs/engineering/slo.md) and [the runbook](docs/engineering/runbook.md).

![Gateway dashboard](docs/images/dashboard.png)

**Compliance module (prototype)**
- The EU AI Act classifier is a set of written rules, not a model. Each result names the articles it used, and 15 tests pin the rules down. It follows the amended Act as I read it on a reference site, and it is not yet checked line by line against EUR-Lex.
- A web API classifies a described system, stores every result, and records a reviewer's approve or reject decision. Misspelled fields are rejected instead of ignored.
- Results and reviews go into an append-only Postgres audit log. The application's database user can only read and add rows, triggers block changes for everyone else, and tests prove the refusals, in CI as well. A database administrator could still switch triggers off.
- The reviewer name is typed, not authenticated. There is no login.
- A two-page Streamlit interface (copilot and audit trail) calls the API. It is a test harness, and real pages matching my design previews are planned.
- The AI step is described below.

## AI in Gatekeeper

Where AI is used, what it is allowed to decide, and what is not built yet.

**The AI never decides the compliance result.** Written rules decide the risk tier, so the same answers always give the same result and every result cites the articles it used. The AI helps with reading and writing text, and a person confirms.

| Part | What it does | Status |
| --- | --- | --- |
| AI gateway (LiteLLM, configured by me, not written by me) | One door for all model calls, with a key and a budget per team. Claude Haiku answers, and Claude Sonnet takes over if it fails | Built and tested |
| Outage drills | I broke the primary model on purpose and checked that the backup answered and that an alert fired and cleared | Done, evidence in the logbook |
| AI monitoring | Requests per model, failures, backup use, a written 99% target and three alerts, in Prometheus and Grafana | Built |
| Answer proposals from free text | `POST /extractions` sends a description through the gateway, and the model proposes answers to the questionnaire, each with a quote from the description | Built, checked on a real model |
| AI-written explanation using only the cited articles | The model explains the result, and the code rejects any mention of an article the rules did not cite | Planned |
| Exact article text under "Sources" | Lookup of the cited articles | Planned |
| Vector search over the whole AI Act | Retrieval for free-text questions about the Act | Not built, only if time allows |
| Personal-data masking and rate limiting | A minimal version before any public demo | Planned |
| Quality gate in CI for the AI step | A test set that blocks a release if answers get worse | Planned |
| Langfuse traces | Cloud tier, synthetic data only | Planned |
| LangChain, agents, fine-tuning | | Not used |

### How the proposal step is kept safe

- The model only proposes. A person confirms, and the rules decide the tier.
- Every proposal must quote the description. The code checks that the quote really is in the text, and pre-fills nothing otherwise.
- The model must answer in a fixed JSON shape. Unknown fields, wrong types and duplicates are dropped and counted.
- Answers that can change the result (Annex III areas, profiling, the exceptions) are pre-filled only when the model is highly sure.
- Prohibited practices and "outside the EU" are never pre-filled, so a prompt injection cannot produce a banned result without a person.
- The prompt tells the model that the description is untrusted data. Descriptions are limited to 4000 characters. Enter synthetic or public data only.
- Gateway errors are reported without the key, and nothing is guessed when the model fails.

### How it is tested

38 tests cover the step with a fake gateway, so no paid call is needed: quote checking, wrong types, duplicates, prompt injection, the confidence rules and the gateway client. A live run on the real model found something the fake could not: the newer Claude model rejects `temperature: 0`, so answers can vary between runs. That is why no answer is trusted without a verified quote and a person's confirmation.

## What is not built yet

The compliance service and its interface run locally and are not yet deployed through Argo CD. Also planned: the AI-written explanation, exact article text under the results, real pages matching my design previews, personal-data masking and rate limiting, a quality gate for the AI step in CI, Langfuse traces, and the product documents (case study and user interviews). Each is listed above only once it works.

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