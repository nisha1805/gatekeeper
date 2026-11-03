#!/bin/sh
# Pod-kill test: delete the gateway pod, then record how long until a new pod is ready
# and what Prometheus saw. Needs KUBECONFIG set and a port-forward to Prometheus on 9090.
set -u
PROM=http://localhost:9090
NS=gateway

pods() { kubectl -n "$NS" get pods -l app.kubernetes.io/name=litellm --no-headers 2>/dev/null | grep -v migrations; }
up_value() { curl -s -G "$PROM/api/v1/query" --data-urlencode 'query=up{job="litellm"}' | python3 -c 'import sys,json; r=json.load(sys.stdin)["data"]["result"]; print(r[0]["value"][1] if r else "none")'; }
alerts() { curl -s "$PROM/api/v1/alerts" | python3 -c 'import sys,json; a=json.load(sys.stdin)["data"]["alerts"]; print(",".join(x["labels"]["alertname"]+":"+x["state"] for x in a) or "none")'; }

OLD=$(pods | awk '$3=="Running"{print $1; exit}')
[ -n "$OLD" ] || { echo "No running gateway pod found"; exit 2; }
echo "Deleting pod $OLD"
START=$(date +%s)
kubectl -n "$NS" delete pod "$OLD" --wait=false >/dev/null

READY_AT=""
SAW_DOWN=no
i=0
while [ "$i" -lt 60 ]; do
  T=$(( $(date +%s) - START ))
  P=$(pods | awk '{printf "%s[%s %s] ", substr($1,length($1)-4), $2, $3}')
  U=$(up_value)
  A=$(alerts)
  echo "t+${T}s  pods: ${P:-none}  up=${U}  alerts: ${A}"
  if [ "$U" = "0" ] || [ "$U" = "none" ]; then SAW_DOWN=yes; fi
  if [ -z "$READY_AT" ]; then
    NEW=$(pods | awk -v old="$OLD" '$1!=old && $2=="1/1" && $3=="Running"{print $1; exit}')
    [ -n "$NEW" ] && READY_AT=$T
  fi
  if [ -n "$READY_AT" ] && [ "$U" = "1" ]; then break; fi
  sleep 5
  i=$((i+1))
done
echo "----"
echo "New pod ready after: ${READY_AT:-not within 300} seconds"
echo "Prometheus saw the target down: $SAW_DOWN"