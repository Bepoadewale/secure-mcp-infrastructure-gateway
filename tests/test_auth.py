from __future__ import annotations

import jwt
from mcpgw.auth import AUDIENCE, ISSUER, JwtVerifier, LocalJwtAuthority


def _token(authority: LocalJwtAuthority, **overrides: object) -> str:
    values: dict[str, object] = {
        "subject": "alice",
        "principal_type": "human",
        "team": "payments",
        "roles": ["developer"],
        "scopes": ["infra.write"],
    }
    values.update(overrides)
    return authority.issue(**values)  # type: ignore[arg-type]


def test_jwt_verifier_accepts_ed25519_identity_and_rejects_bad_claims() -> None:
    authority = LocalJwtAuthority.generate()
    verifier = JwtVerifier(authority.jwks())
    identity = verifier.verify(_token(authority, principal_type="agent"))
    assert identity.principal_type == "agent"

    for overrides in (
        {"lifetime_seconds": -1},
        {"issuer": "https://wrong-issuer.test"},
        {"audience": "wrong-audience"},
    ):
        try:
            verifier.verify(_token(authority, **overrides))
        except PermissionError:
            pass
        else:
            raise AssertionError("invalid token was accepted")


def test_jwt_verifier_rejects_unsigned_and_wrong_signing_key() -> None:
    authority = LocalJwtAuthority.generate()
    verifier = JwtVerifier(authority.jwks())
    unsigned = jwt.encode(
        {"sub": "alice", "team": "payments", "principal_type": "human", "iss": ISSUER, "aud": AUDIENCE},
        key="",
        algorithm="none",
    )
    for token in (unsigned, _token(LocalJwtAuthority.generate())):
        try:
            verifier.verify(token)
        except PermissionError:
            pass
        else:
            raise AssertionError("untrusted token was accepted")
