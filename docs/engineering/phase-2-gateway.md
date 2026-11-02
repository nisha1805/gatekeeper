# Phase 2: gateway

## What was built
- Secrets: keys live in git-ignored .env files. scripts/create-secrets.sh loads them into a Kubernetes secret. scripts/seed-teams.sh creates two teams and keys after each rebuild.
- Postgres 16 as a StatefulSet (deploy/postgres), password read from the secret.
- LiteLLM from the official Helm chart (version 1.106.6, image v1.106.6), pinned, delivered through Argo CD. Chart database and Redis switched off.
- Two models, chat-primary (Haiku) and chat-backup (Sonnet), with a fallback rule and one retry.
- Per-team budgets and virtual keys. Smoke test: scripts/smoke-test.sh.

## Tested
- Outage drill: primary broken by a Git commit, request answered by the backup (header x-litellm-attempted-fallbacks: 1), repaired with git revert.
- Budgets: a team with a tiny budget was blocked with HTTP 422 after four requests. Its spend ended at 3.55e-05 against a cap of 3e-05.
- Smoke test: 6 of 6 checks passed after a full rebuild.

## Decisions
- LiteLLM is configured and tested, not built.
- The gateway uses the Recreate update strategy so two pods never run at once. This saves memory on a laptop, but means a short gap in service on every restart.
- The fallback is tested with a real failure. LiteLLM ignores the mock-testing flag on proxy requests from version 1.85.
- Each model is tested on its own before the fallback is trusted.

## Problems I hit
- A duplicated model entry left chat-backup undefined, so the first drill returned HTTP 500. The log said there were no healthy deployments for it.
- The laptop ran out of memory (Docker had 1 CPU and 4 GiB, with many other apps open), so kubectl timed out. Docker now has 8 CPUs and 5 GiB.

## Known limits
- Fallback is a larger model, about 20 times the cost per request in the price list. A long outage would spend budget faster.
- Budget enforcement overshoots slightly.
- The root-container policy covers three namespaces only (hello-dev, hello-prod, gateway), not the whole cluster. It checks regular containers, not init containers.
- No guardrails and no network policy yet. Local single-node cluster only.

## Hardening (added after the first notes)
- Postgres runs as user 70 with all capabilities dropped. The gateway runs as user 65534 on the official non-root image (litellm-non_root, same version as before).
- The Kyverno rule now covers the gateway namespace and accepts the non-root setting at pod level or container level.
- Tested: a root pod was refused in gateway and hello-dev, the hardened Postgres pod was admitted after deletion, and the smoke test passed 6 of 6 both before and after hardening.

## Problem I hit while hardening
- My first gateway commit was described as switching to the non-root image, but the repository line had not changed. The pod still ran as nobody because the pod-level settings were enough, and the smoke test passed either way. I found it by reading the running deployment's image and user, and fixed it with a second commit.