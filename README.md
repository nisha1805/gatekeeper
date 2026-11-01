# Gatekeeper

An AI gateway with EU AI Act compliance workflows, built as a hands-on portfolio project.

**Status: work in progress. Prototype only, no real users.** Nothing here is production-ready.

## The problem

When several teams add AI features, three things get out of control: cost (nobody knows what an answer costs), quality (prompts and models change without measurement) and compliance (EU AI Act duties need classification and evidence). See [the problem brief](docs/product/problem-brief.md).

## What I plan to build

- A gateway in front of several models, with per-team keys, budgets and fallback
- Observability: traces, cost, latency and written SLOs
- A CI pipeline that blocks a release when measured quality or cost gets worse
- A small compliance copilot that classifies an AI system and keeps an audit trail
- Everything deployed with Terraform and GitOps on a local Kubernetes cluster

Only the folder structure and the problem brief exist so far. This README will be updated as each part is actually built.

## Inspired by and built on

Planned building blocks. Each entry will be confirmed, with its licence checked, when I actually use it:

- LiteLLM: planned gateway
- Langfuse: planned tracing and cost
- Argo CD: planned GitOps delivery
- kind and Terraform: planned local cluster

## Honesty notes

- Public and synthetic data only. Nothing from any employer.
- This is decision support, not legal advice.
- I will only claim what I have built, and only report numbers I can reproduce.

## Licence

MIT. See [LICENSE](LICENSE).