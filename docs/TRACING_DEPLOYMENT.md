# Tracing Deployment Validation

Run tracing readiness check:

```powershell
.\.venv\Scripts\python.exe scripts\run_tracing_check.py
```

Expected fields:
- `langsmith_ready`: true when tracing flag + API key + project are configured.
- `deepflow_reachable`: true when DeepFlow endpoint is reachable on `DEEPFLOW_HOST:DEEPFLOW_PORT`.

Environment variables:
- `LANGCHAIN_TRACING_V2`
- `LANGCHAIN_API_KEY`
- `LANGCHAIN_PROJECT`
- `DEEPFLOW_HOST` (default `localhost`)
- `DEEPFLOW_PORT` (default `20035`)
