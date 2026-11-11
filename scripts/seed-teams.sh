#!/bin/sh
# Creates team-a, team-b and compliance-service with budgets and one key each.
# Needs the gateway reachable on localhost:4000 (port-forward). Run once per rebuild.
set -eu
set -a
. ./.env
set +a
URL=http://localhost:4000
AUTH="Authorization: Bearer $LITELLM_MASTER_KEY"

json_field() { python3 -c 'import sys,json; print(json.load(sys.stdin)["'"$1"'"])'; }

make_team() {
  curl -sf "$URL/team/new" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"team_alias\":\"$1\",\"max_budget\":$2,\"budget_duration\":\"30d\"}" | json_field team_id
}
make_key() {
  curl -sf "$URL/key/generate" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"team_id\":\"$1\",\"key_alias\":\"$2\"}" | json_field key
}

A_ID=$(make_team team-a 0.05)
B_ID=$(make_team team-b 0.00003)
C_ID=$(make_team compliance-service 1.00)
A_KEY=$(make_key "$A_ID" team-a-key)
B_KEY=$(make_key "$B_ID" team-b-key)
C_KEY=$(make_key "$C_ID" compliance-service-key)

umask 077
printf 'TEAM_A_KEY=%s\nTEAM_B_KEY=%s\nCOMPLIANCE_KEY=%s\n' "$A_KEY" "$B_KEY" "$C_KEY" > .env.teams
echo "Created team-a, team-b and compliance-service. Keys saved to .env.teams (git-ignored)."
