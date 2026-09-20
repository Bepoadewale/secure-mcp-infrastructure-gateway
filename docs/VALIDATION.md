# Validation

Run `PYTHONPATH=gateway/src python3 -m pytest -q` and lint once configured. Live status requires versions, services, captured `tools/list` and `tools/call` interactions, signed-token validation, enforced policy denial, audit persistence, and failure evidence; mocked method names are insufficient. Never fabricate validation.
