# Interactive Operator Dashboard

The API now includes an interactive operator deck for trading telemetry and insight triage.

## Route
- `GET /dashboard`

## Data feeds used by the page
- `GET /api/dashboard/overview`
- `GET /api/dashboard/insights?lookback_hours=24`
- `GET /api/portfolio/equity-curve?lookback_hours=24`
- `GET /api/strategies/pending-validation`

## Features
- Live KPI cards: PnL, win-rate, profit factor, drawdown, pass-rate, confidence, regime, risk level.
- Equity curve chart with selectable windows (`24h`, `72h`, `7d`).
- Agent health and pending-validation tables.
- Operator insight list generated from trade quality, validation quality, slippage, and risk-event posture.
- Auto-refresh every 15 seconds.
