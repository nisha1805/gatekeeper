#!/bin/sh
# Print one value per minute for a query over the last N minutes (default 30).
# Usage: scripts/promrange.sh 'query' [minutes]
set -eu
M=${2:-30}
END=$(date +%s)
START=$((END-M*60))
curl -sf -G http://localhost:9090/api/v1/query_range --data-urlencode "query=$1" --data-urlencode "start=$START" --data-urlencode "end=$END" --data-urlencode "step=60" \
  | python3 -c 'import sys,json,datetime; d=json.load(sys.stdin)["data"]["result"]; [print(datetime.datetime.fromtimestamp(float(t)).strftime("%H:%M"), v) for s in d for t,v in s["values"]] if d else print("no data")'