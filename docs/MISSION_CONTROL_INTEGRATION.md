# Mission Control Upstream Integration

This project now uses the upstream repository at:

- `mission-control-upstream/`

## Run with docker compose

```powershell
docker compose up -d mission-control swarm-api redis timescaledb
```

Mission Control will be available at `http://localhost:3000`.

Default credentials are read from `.env`:
- `MC_USER`
- `MC_PASS`
- `MC_API_KEY`

## Notes

- Compose builds from `./mission-control-upstream`.
- Runtime data persists in docker volume `mission_control_data`.
- Gateway host defaults to `swarm-api:8000` inside compose network.
- Replace defaults before internet-exposed deployments.
