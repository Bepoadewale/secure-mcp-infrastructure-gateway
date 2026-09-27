"""Local Ed25519 JWT/JWKS identity verification for the gateway."""

from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jwt import PyJWK

ISSUER = "https://local.secure-mcp-gateway.test"
AUDIENCE = "secure-mcp-infrastructure-gateway"


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


@dataclass(frozen=True)
class Identity:
    subject: str
    principal_type: str
    team: str
    roles: frozenset[str]
    scopes: frozenset[str]
    delegated_by: str | None = None


class LocalJwtAuthority:
    """Creates synthetic local identities; its private key is never a device credential."""

    def __init__(self, private_key: Ed25519PrivateKey, kid: str = "local-ed25519-1") -> None:
        self._private_key = private_key
        self.kid = kid

    @classmethod
    def generate(cls) -> LocalJwtAuthority:
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def load_or_create(cls, path: str) -> LocalJwtAuthority:
        """Persist a synthetic development signer only under the project-local state directory."""
        key_path = os.fspath(path)
        try:
            with open(key_path, "rb") as key_file:
                private_key = serialization.load_pem_private_key(key_file.read(), password=None)
        except FileNotFoundError:
            os.makedirs(os.path.dirname(key_path) or ".", exist_ok=True)
            private_key = Ed25519PrivateKey.generate()
            encoded = private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
            descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as key_file:
                key_file.write(encoded)
        if not isinstance(private_key, Ed25519PrivateKey):
            raise TypeError("local signer must be an Ed25519 private key")
        return cls(private_key)

    def jwks(self) -> dict[str, list[dict[str, str]]]:
        public = self._private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        return {
            "keys": [
                {
                    "kty": "OKP",
                    "crv": "Ed25519",
                    "x": _base64url(public),
                    "kid": self.kid,
                    "alg": "EdDSA",
                    "use": "sig",
                }
            ]
        }

    def issue(
        self,
        *,
        subject: str,
        principal_type: str,
        team: str,
        roles: list[str],
        scopes: list[str],
        lifetime_seconds: int = 300,
        issuer: str = ISSUER,
        audience: str = AUDIENCE,
        delegated_by: str | None = None,
    ) -> str:
        now = int(time.time())
        claims = {
                "sub": subject,
                "principal_type": principal_type,
                "team": team,
                "roles": roles,
                "scope": " ".join(scopes),
                "iss": issuer,
                "aud": audience,
                "iat": now,
                "exp": now + lifetime_seconds,
            }
        if delegated_by:
            claims["delegated_by"] = delegated_by
        return jwt.encode(
            claims,
            self._private_key,
            algorithm="EdDSA",
            headers={"kid": self.kid},
        )

    def issue_agent_delegation(
        self,
        *,
        human: str,
        agent: str,
        team: str,
        scopes: list[str],
        lifetime_seconds: int = 60,
    ) -> str:
        """Mint a bounded local delegation; agents cannot issue their own authority."""
        if lifetime_seconds <= 0 or lifetime_seconds > 60:
            raise ValueError("agent delegation lifetime must be between 1 and 60 seconds")
        return self.issue(
            subject=agent,
            principal_type="agent",
            team=team,
            roles=["agent"],
            scopes=scopes,
            lifetime_seconds=lifetime_seconds,
            delegated_by=human,
        )


class JwtVerifier:
    def __init__(self, jwks: dict[str, list[dict[str, str]]], issuer: str = ISSUER, audience: str = AUDIENCE) -> None:
        self._keys = {entry["kid"]: PyJWK.from_dict(entry).key for entry in jwks["keys"]}
        self._issuer = issuer
        self._audience = audience

    def verify(self, token: str) -> Identity:
        try:
            header = jwt.get_unverified_header(token)
            key = self._keys[header["kid"]]
            claims = jwt.decode(
                token,
                key,
                algorithms=["EdDSA"],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["exp", "sub", "iss", "aud", "team", "principal_type"]},
            )
        except (KeyError, jwt.PyJWTError) as exc:
            raise PermissionError("invalid gateway identity") from exc
        principal_type = claims["principal_type"]
        if principal_type not in {"human", "agent", "client", "service"}:
            raise PermissionError("unsupported principal type")
        delegated_by = claims.get("delegated_by")
        if principal_type == "agent" and not delegated_by:
            raise PermissionError("agent identity requires a delegated human authority")
        return Identity(
            subject=claims["sub"],
            principal_type=principal_type,
            team=claims["team"],
            roles=frozenset(claims.get("roles", [])),
            scopes=frozenset(claims.get("scope", "").split()),
            delegated_by=delegated_by,
        )
