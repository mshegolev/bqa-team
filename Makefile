.PHONY: test lint verify

PYTHON ?= python3

test:
	$(PYTHON) -m unittest discover -s tests -v

lint:
	$(PYTHON) -m py_compile scripts/bqa_team_orchestrator.py tests/*.py
	bash -n scripts/*.sh

verify: lint test
