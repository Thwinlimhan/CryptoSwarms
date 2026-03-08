# Runbook: Circuit Breaker Event

## Trigger
- Daily drawdown breach
- Portfolio heat breach
- Risk monitor stale heartbeat

## Immediate Actions
1. Verify `execution:halt` event in Mission Control.
2. Confirm `risk_monitor:heartbeat` key freshness in Redis.
3. Snapshot open positions and exposure by venue.

## Recovery
1. Identify root cause (signal quality, latency, venue outage).
2. Keep entries halted until drawdown and heat are within policy.
3. Resume only with explicit operator CONFIRM and documented rationale.

## Post-Incident
1. Append immutable audit entry.
2. Update weekly review with corrective actions.
