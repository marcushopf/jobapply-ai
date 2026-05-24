VENV = .venv/bin
PYTEST = $(VENV)/pytest

.PHONY: test test-integration test-integration-refresh test-e2e test-all install

## Fast unit tests — no LLM, no network. Run these constantly.
test:
	$(PYTEST) tests/unit/ -v

## Integration tests — uses cached LLM responses (no quota burned). Run often.
test-integration:
	$(PYTEST) tests/integration/ -v

## Integration tests — forces fresh Gemini API calls and rebuilds cache.
## Run this when prompts or logic change, not on every commit.
test-integration-refresh:
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
