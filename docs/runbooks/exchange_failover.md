# Runbook: Exchange Failure / Failover

## Trigger
- Consecutive adapter failures
- Venue API outage

## Immediate Actions
1. Confirm failing venue and error class.
2. Route to next approved adapter via failover executor.
3. Record failover event in immutable audit log.

## Recovery
1. Re-test primary adapter with paper order.
2. Restore primary only after 3 consecutive healthy checks.
3. Keep reduced position size for first 5 resumed entries.

## Post-Incident
1. Export error timeline from logs.
2. Add venue reliability note to weekly review.
