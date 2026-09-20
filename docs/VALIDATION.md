# Validation

Run `PYTHONPATH=gateway/src python3 -m pytest -q` and lint once configured. Live status requires versions, services, captured `tools/list` and `tools/call` interactions, signed-token validation, enforced policy denial, audit persistence, and failure evidence; mocked method names are insufficient. Never fabricate validation.

## Clean-Room Validation

Do not populate this section until executed. Record: date, commit SHA, OS/environment, Docker/kind/Kubernetes and key dependency versions where applicable; clean starting state; exact install/bootstrap/smoke/demo/failure/validation/cleanup commands; observed results; post-cleanup absence verification; and the second-bootstrap result. No prior local state or fabricated evidence is acceptable.
