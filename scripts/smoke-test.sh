#!/bin/sh
# Smoke test for the gateway. Run from the repo root.
# Needs: a port-forward on localhost:4000, plus .env and .env.teams (both git-ignored).
set -u
URL=${GATEWAY_URL:-http://localhost:4000}

for f in .env .env.teams; do
  [ -f "$f" ] || { echo "Missing $f. Run scripts/create-secrets.sh and scripts/seed-teams.sh first."; exit 2; }
done
set -a
. ./.env
. ./.env.teams
set +a

PASS=0
FAIL=0
ok()  { echo "PASS  $1"; PASS=$((PASS+1)); }
bad() { echo "FAIL  $1"; FAIL=$((FAIL+1)); }

# Prints the full response, headers first.
chat() {
  curl -si --max-time 60 "$URL/v1/chat/completions" \
    -H "Authorization: Bearer $1" -H "Content-Type: application/json" \
    -d "{\"model\":\"$2\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello in five words\"}],\"max_tokens\":30}"
}
# Prints only the HTTP status code.
code() {
  curl -s -o /dev/null -w "%{http_code}" --max-time 60 "$URL/v1/chat/completions" \
    -H "Authorization: Bearer $1" -H "Content-Type: application/json" \
    -d "{\"model\":\"$2\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello in five words\"}],\"max_tokens\":30}"
}

# 1. Gateway is up and connected to its database
R=$(curl -s --max-time 10 "$URL/health/readiness")
echo "$R" | grep -q '"db":"connected"' && ok "gateway healthy, database connected" || bad "readiness check returned: $R"

# 2. Primary model answers (Haiku)
R=$(chat "$LITELLM_MASTER_KEY" chat-primary)
if echo "$R" | head -1 | grep -q " 200" && echo "$R" | grep -qi "x-litellm-model-name: anthropic/claude-haiku"; then
  ok "chat-primary answers from Haiku"
else bad "chat-primary did not answer from Haiku"; fi

# 3. Backup model answers on its own (Sonnet)
R=$(chat "$LITELLM_MASTER_KEY" chat-backup)
if echo "$R" | head -1 | grep -q " 200" && echo "$R" | grep -qi "x-litellm-model-name: anthropic/claude-sonnet"; then
  ok "chat-backup answers from Sonnet"
else bad "chat-backup did not answer from Sonnet"; fi

# 4. Team A key works
[ "$(code "$TEAM_A_KEY" chat-primary)" = "200" ] && ok "team A key works" || bad "team A key did not return 200"

# 5. Team B is blocked once its tiny budget is used up (tries up to 10 requests)
BLOCKED=0
for i in 1 2 3 4 5 6 7 8 9 10; do
  if [ "$(code "$TEAM_B_KEY" chat-primary)" = "422" ]; then BLOCKED=$i; break; fi
done
[ "$BLOCKED" -gt 0 ] && ok "team B blocked by its budget (on request $BLOCKED)" || bad "team B was never blocked in 10 requests"

# 6. Team A is unaffected by team B being blocked
[ "$(code "$TEAM_A_KEY" chat-primary)" = "200" ] && ok "team A still works while team B is blocked" || bad "team A affected by team B"

echo "----"
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]