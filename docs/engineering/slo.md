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

## What was tested (3 Nov 2026)
- Pod kill: a new gateway pod was ready after about 45 seconds. Prometheus saw the target down for roughly 30 seconds. GatewayMetricsDown did not fire, because its hold time is 1 minute.
- Fallback: with the primary model broken, 8 of 8 requests succeeded, the fallback counter reached 8 and GatewayFallbackActive fired. It cleared by itself after the primary was repaired.
- Error rate: with both models broken, every request returned HTTP 500, but the first version of the success-ratio rule never fired, because with no successes the ratio became an empty result. The rule now treats no successes as zero. The fix was checked by replaying recorded data, where the ratio was 0 for ten minutes in a row. It has not been seen firing live.

## Limits found by testing
- With one gateway replica, every restart is about 45 seconds of unavailability. The effect on requests was not measured.
- A degraded service running on the backup model does not move the success ratio, so it has its own alert.
- Scrape-based monitoring can miss an outage shorter than the scrape interval (30 seconds).
- A gateway that is completely unreachable is covered by GatewayMetricsDown, not by the ratio rule.