# Service level objective: gateway chat requests

## The indicator (SLI)
Of the chat requests that reach the gateway and are not the client's own fault, the share that succeed.
- Good: HTTP 2xx on /v1/chat/completions.
- Bad: HTTP 5xx.
- Excluded: HTTP 4xx (wrong key, budget exceeded, bad request, rate limiting). The gateway refusing these is correct behaviour.
It is computed in Prometheus as the recording rule gatekeeper:chat_success_ratio:rate5m.

## The objective (SLO)
Design target: 99% of eligible chat requests succeed. The error budget is therefore 1 in 100 requests.
This is a target I chose, not a measured result. Prometheus here keeps only 6 hours of data, so a 30-day window cannot be evaluated on this lab.

## Alerts (lab thresholds, not tuned)
- GatewayChatErrorsHigh (page): fewer than 95% of chat requests succeeded over 5 minutes, for 2 minutes.
- GatewayMetricsDown (page): the gateway metrics cannot be scraped for 1 minute.
- GatewayFallbackActive (ticket): the backup model has answered requests in the last 5 minutes.

## Known limits
- No Alertmanager: alerts appear on the Prometheus Alerts page, and nobody is notified.
- Low traffic makes the ratio jumpy, because a few failed requests move it a lot.
- Production practice would use burn-rate alerts over several windows and a longer retention.
- The fallback alert's metric name still has to be verified against real data.