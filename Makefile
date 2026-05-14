.PHONY: help install up down db-init smoke week1 week2 week3-ingest week3 week5 mcp serve frontend eval test clean

help:
	@echo "Targets:"
	@echo "  install        pip install -r requirements.txt"
	@echo "  up             docker compose up -d (pgvector)"
	@echo "  down           docker compose down"
	@echo "  db-init        apply scripts/setup_db.sql to the running pg container"
	@echo "  smoke          quick import + chunking tests (no network, no DB)"
	@echo "  week1 Q='...'  one-agent run"
	@echo "  week2 Q='...'  3-agent crew (no RAG)"
	@echo "  week3-ingest T='topic' N=50    ingest papers"
	@echo "  week3 Q='...'  crew with vector_search"
	@echo "  week5 Q='...'  LangGraph workflow"
	@echo "  mcp            run the MCP server on stdio"
	@echo "  serve          uvicorn FastAPI on :8000"
	@echo "  eval N=5       run Ragas on first N golden questions"
	@echo "  test           full pytest"
	@echo "  clean          remove caches"

install:
	pip install --upgrade pip
	pip install -r requirements.txt

up:
	docker compose up -d

down:
	docker compose down

db-init:
	docker exec -i deep-research-pg psql -U postgres -d multi_agent_system < scripts/setup_db.sql

smoke:
	python -m pytest -q tests/test_smoke.py -k "imports or chunking or schema"

week1:
	python scripts/run_week1.py "$(Q)"

week2:
	python scripts/run_week2.py "$(Q)"

week3-ingest:
	python scripts/run_week3_ingest.py --topic "$(T)" --limit $(or $(N),50)

week3:
	python scripts/run_week3.py "$(Q)"

week5:
	python scripts/run_week5.py "$(Q)"

mcp:
	python -m src.mcp_server.server

serve:
	uvicorn src.api.main:app --reload --port 8000

frontend:
	streamlit run frontend/app.py

eval:
	python -m src.evals.ragas_eval --limit $(or $(N),0)

test:
	python -m pytest -q

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
