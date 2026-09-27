.DEFAULT_GOAL := help

.PHONY: help install bootstrap-local smoke demo-mcp demo-security verify clean-local

help:
	@printf '%s\n' 'Targets: install bootstrap-local smoke demo-mcp demo-security verify clean-local'

install:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -e '.[dev]'

bootstrap-local:
	./scripts/bootstrap-local.sh

smoke:
	./scripts/smoke.sh

demo-mcp:
	./scripts/demo-mcp.sh

demo-security:
	./scripts/demo-security.sh

verify:
	.venv/bin/python -m ruff check gateway/src fixtures tests
	.venv/bin/python -m pytest -q

clean-local:
	./scripts/clean-local.sh
