# Gatekeeper: problem brief

## Who is this for?

Main user: platform engineers who run the shared AI infrastructure for several product teams.

Also: AI product teams who build features on top of it, and compliance partners who need evidence of how AI systems are used.

## What problem do they have?

When several teams add AI features, three things get out of control.

**Cost.** Each team has its own API keys, so nobody can say what one answer costs or which team is spending what.

**Quality.** Prompts and models change without anyone measuring whether the answers got better or worse. A release can make things worse and nobody notices.

**Compliance.** The EU AI Act expects companies to know which AI systems they run, classify them and keep evidence. Most teams do this by hand in documents, if at all.

## What is the evidence?

To be gathered through 3 to 5 interviews with people who build or run AI features (Phase 6). Until then, this brief describes a hypothesis, not a proven problem.

## Why now?

Draft: AI features are spreading across teams, and the EU AI Act is phasing in. The exact dates will be checked against the official text on EUR-Lex before anything is published (Phase 5).

## What we will not build

- Not a new gateway from scratch. Gatekeeper is built on LiteLLM, Langfuse and other open-source tools.
- Not legal advice. The compliance module is decision support only.
- Not a replacement for lawyers or for repo-scanning tools such as EuConform.
- No real company data. Public or synthetic data only.
- Not production-ready. It is a prototype with no real users.

## Status

Prototype. Built on public and synthetic data only. Decision support, not legal advice.