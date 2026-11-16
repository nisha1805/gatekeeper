#!/bin/sh
# Creates the compliance-secrets secret. Run from the repo root, with KUBECONFIG set.
# Needs .env.teams (git-ignored) for COMPLIANCE_KEY, the gateway key of the compliance team.
# Passwords are generated here, never stored in Git. If the secret already exists it is left
# alone, because the database keeps the old passwords in its volume.
set -eu
[ -f .env.teams ] || { echo "Missing .env.teams. Run scripts/seed-teams.sh first."; exit 2; }
set -a
. ./.env.teams
set +a
: "${COMPLIANCE_KEY:?COMPLIANCE_KEY is missing in .env.teams}"
if kubectl -n compliance get secret compliance-secrets >/dev/null 2>&1; then
  echo "compliance-secrets already exists: left unchanged"
  exit 0
fi
ADMIN_PW=$(openssl rand -hex 16)
APP_PW=$(openssl rand -hex 16)
kubectl -n compliance create secret generic compliance-secrets \
  --from-literal=POSTGRES_PASSWORD="$ADMIN_PW" \
  --from-literal=APP_PASSWORD="$APP_PW" \
  --from-literal=ADMIN_DATABASE_URL="postgresql://postgres:${ADMIN_PW}@compliance-postgres:5432/compliance" \
  --from-literal=DATABASE_URL="postgresql://compliance_app:${APP_PW}@compliance-postgres:5432/compliance" \
  --from-literal=GATEWAY_API_KEY="$COMPLIANCE_KEY"
echo "compliance-secrets created"
