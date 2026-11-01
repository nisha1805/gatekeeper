#!/bin/sh
# Copies the values in .env into a Kubernetes secret. Run from the repo root.
set -eu
set -a
. ./.env
set +a
kubectl -n gateway create secret generic litellm-secrets \
  --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  --from-literal=LITELLM_MASTER_KEY="$LITELLM_MASTER_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -