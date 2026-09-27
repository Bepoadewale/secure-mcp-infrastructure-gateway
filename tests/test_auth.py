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
    identity = verifier.verify(_token(authority, principal_type="agent", delegated_by="alice"))
    assert identity.principal_type == "agent"
    assert identity.delegated_by == "alice"
    assert verifier.verify(_token(authority, principal_type="client")).principal_type == "client"

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


def test_agent_delegation_is_short_lived_and_cannot_be_self_issued() -> None:
    authority = LocalJwtAuthority.generate()
    verifier = JwtVerifier(authority.jwks())
    delegated = authority.issue_agent_delegation(
        human="alice",
        agent="agent-1",
        team="payments",
        scopes=["infra.read"],
    )
    assert verifier.verify(delegated).delegated_by == "alice"
    expired = _token(
        authority,
        principal_type="agent",
        delegated_by="alice",
        lifetime_seconds=-1,
    )
    try:
        verifier.verify(expired)
    except PermissionError:
        pass
    else:
        raise AssertionError("expired delegation was accepted")
    try:
        verifier.verify(_token(authority, principal_type="agent"))
    except PermissionError:
        pass
    else:
        raise AssertionError("agent without delegation was accepted")
    try:
        authority.issue_agent_delegation(
            human="alice",
            agent="agent-1",
            team="payments",
            scopes=["infra.read"],
            lifetime_seconds=61,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("long delegation was accepted")
