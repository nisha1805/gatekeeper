#!/bin/sh
# Ask the local Prometheus (port-forward on 9090) one question and print each result.
# Usage: scripts/promq.sh 'sum by (status_code) (litellm_proxy_total_requests_metric_total)'
set -eu
curl -sf -G http://localhost:9090/api/v1/query --data-urlencode "query=$1" \
  | python3 -c 'import sys,json; [print(r["metric"], r["value"][1]) for r in json.load(sys.stdin)["data"]["result"]]'