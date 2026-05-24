VENV = .venv/bin
PYTEST = $(VENV)/pytest

.PHONY: test test-integration test-e2e test-all install

## Fast unit tests — no LLM, no network. Run these constantly.
test:
	$(PYTEST) tests/unit/ -v

## Integration tests — real Gemini API calls. Run before committing.
test-integration:
	$(PYTEST) tests/integration/ -v

## Full end-to-end pipeline for Alex Müller (all 6 stages). Slow.
test-e2e:
	$(PYTEST) tests/e2e/ -v -s

## Everything
test-all:
	$(PYTEST) tests/ -v

## Install all dependencies into venv
install:
	$(VENV)/pip install -r requirements.txt
