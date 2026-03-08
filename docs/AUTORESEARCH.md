# AutoResearch Integration

Autoresearch patterns are implemented in `agents/evolution/autoresearch.py`.

## What is implemented
- Time-boxed nightly experiment loop via `max_runtime_minutes`.
- Program-controlled policy loaded from `agents/evolution/program.md`.
- Keep/discard gate using minimum score improvement vs incumbent.
- Promotion cap using `keep_top_k`.

## Run

```powershell
.\.venv\Scripts\python.exe scripts\run_evolution_autoresearch.py
```

Optional environment variables:
- `AUTORESEARCH_PROGRAM_PATH`: override path to policy markdown.
- `AUTORESEARCH_INCUMBENT_SCORE`: baseline incumbent score for promotion checks.
