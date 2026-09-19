# Validation

Run `PYTHONPATH=gateway/src python3 -m pytest -q` and lint once configured. Live status requires captured `tools/list` and `tools/call` fixture interactions, signed-token validation, an enforced policy denial and audit persistence; mocked method names are insufficient.
