# Runbook: gateway alerts

Commands assume KUBECONFIG points at the cluster, and a port-forward to Prometheus on 9090 for the query helper.

## Before any change
- Run `git log --oneline -3`. Revert a bad change by commit name (`git revert --no-edit <commit>`), never by HEAD after other commits were added, because a second revert undoes the first.
- After any fix, run `scripts/smoke-test.sh`. It must show 6 passed.

## GatewayMetricsDown (page)
Meaning: Prometheus could not scrape the gateway metrics port for a full minute.
1. `kubectl -n gateway get pods`. If the gateway pod is restarting or not 1/1, a restart takes about 45 seconds. Wait before acting.
2. If it stays down: `kubectl -n gateway describe pod -l app.kubernetes.io/name=litellm` and `kubectl -n gateway logs deploy/litellm --tail=50`.
3. A crash soon after a push usually means a config mistake. Check `git log --oneline -3` and revert that commit by name.
4. If the pod is healthy but the target is down, check that the litellm-metrics service exists (`kubectl -n gateway get svc`).

## GatewayChatErrorsHigh (page)
Meaning: fewer than 95% of eligible chat requests succeeded over 5 minutes, held for 2 minutes. Client errors (4xx) do not count.
1. Which errors? `scripts/promq.sh 'sum by (status_code) (increase(litellm_proxy_total_requests_metric_total{route="/v1/chat/completions"}[5m]))'`
2. Why? `kubectl -n gateway logs deploy/litellm --tail=50`. Look for provider errors or database errors.
3. Both models failing: check recent commits and revert by name. Check the provider key and credit in the Anthropic console.
4. Database problem: `kubectl -n gateway get pods` and check postgres-0 is 1/1 Running.
Note: a completely unreachable gateway is covered by GatewayMetricsDown, because the ratio has no data then.

## GatewayFallbackActive (ticket)
Meaning: the backup model answered requests in the last 5 minutes. Users see no error, but the primary is failing and the backup costs about 20 times more per request (price-list estimate).
1. `kubectl -n gateway logs deploy/litellm --tail=80 | grep -i fallback`
2. Test the primary alone: run scripts/smoke-test.sh and look at which model answered chat-primary.
3. Fix the cause (config change, provider issue). The alert clears about 5 minutes after the last fallback.

## Known gaps
- There is no Alertmanager, so nobody is notified. Alerts appear on the Prometheus alerts page only.
- One gateway replica means every restart is about 45 seconds of unavailability.
- Prometheus keeps 6 hours of data, and loses it when its pod restarts.