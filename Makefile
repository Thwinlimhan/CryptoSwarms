VENV_PY := .venv\Scripts\python.exe

.PHONY: up down test lint smoke phase1-smoke phase1-loop paper-ledger research-camoufox qdrant-retention research-onchain research-literature tracing-check exchange-skillhub-smoke backtest-runtime-docker autoresearch research-factory

up:
	docker compose up -d

down:
	docker compose down

test:
	$(VENV_PY) -m pytest -q

lint:
	$(VENV_PY) -m py_compile api/main.py cryptoswarms/*.py agents/backtest/*.py agents/execution/*.py agents/research/*.py agents/evolution/*.py scripts/check_backtest_runtimes.py scripts/run_phase1_smoke.py scripts/run_phase1_loop.py scripts/run_paper_ledger_job.py scripts/run_research_camoufox.py scripts/run_qdrant_retention.py scripts/run_research_onchain.py scripts/run_research_literature.py scripts/run_research_factory.py scripts/run_tracing_check.py scripts/run_exchange_skill_hub_smoke.py scripts/run_evolution_autoresearch.py

smoke: phase1-smoke phase1-loop

phase1-smoke:
	$(VENV_PY) scripts/run_phase1_smoke.py

phase1-loop:
	$(VENV_PY) scripts/run_phase1_loop.py

paper-ledger:
	$(VENV_PY) scripts/run_paper_ledger_job.py

research-camoufox:
	$(VENV_PY) scripts/run_research_camoufox.py

qdrant-retention:
	$(VENV_PY) scripts/run_qdrant_retention.py

research-onchain:
	$(VENV_PY) scripts/run_research_onchain.py

research-literature:
	$(VENV_PY) scripts/run_research_literature.py

research-factory:
	$(VENV_PY) scripts/run_research_factory.py

tracing-check:
	$(VENV_PY) scripts/run_tracing_check.py

exchange-skillhub-smoke:
	$(VENV_PY) scripts/run_exchange_skill_hub_smoke.py

autoresearch:
	$(VENV_PY) scripts/run_evolution_autoresearch.py

backtest-runtime-docker:
	pwsh -File scripts/run_backtest_runtime_in_docker.ps1
