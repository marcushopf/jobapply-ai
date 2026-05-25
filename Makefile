VENV = .venv/bin
PYTEST = $(VENV)/pytest

.PHONY: test test-integration test-integration-refresh-ollama test-integration-refresh-gemini test-e2e test-all install

## Fast unit tests — no LLM, no network. Run these constantly.
test:
	$(PYTEST) tests/unit/ -v

## Integration tests — uses cached LLM responses (no quota burned). Run often.
test-integration:
	$(PYTEST) tests/integration/ -v

## Rebuild cache using Ollama (local, unlimited — requires: ollama serve).
## Uses ollama/auto to pick the best model for your hardware automatically.
test-integration-refresh-ollama:
	REFRESH_LLM_CACHE=1 TEST_LLM_MODEL=ollama/auto $(PYTEST) tests/integration/ -v -s

## Rebuild cache using Gemini (production model, slower quota).
test-integration-refresh-gemini:
	REFRESH_LLM_CACHE=1 $(PYTEST) tests/integration/ -v -s

## Full end-to-end pipeline for Sarah Chen (all 6 stages). Slow.
test-e2e:
	$(PYTEST) tests/e2e/ -v -s

## Everything
test-all:
	$(PYTEST) tests/ -v

## Install all dependencies into venv
install:
	$(VENV)/pip install -r requirements.txt
