"""Pydantic schemas for authentication (login, token response, WebAuthn)."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Schema for user login request.

    Attributes:
        username: User's username.
        password: Plain text password.
    """

    username: str
    password: str


class TokenResponse(BaseModel):
    """Schema for JWT token response.

    Attributes:
        access_token: JWT access token string.
        token_type: Always 'bearer'.
        needs_encryption_setup: True if the user has not yet set up encryption.
        is_encrypted: True if the user has encryption enabled.
    """

    access_token: str
    token_type: str = "bearer"
    needs_encryption_setup: bool = False
    is_encrypted: bool = False


class SetupEncryptionRequest(BaseModel):
    """Schema for the encryption setup or unlock request.

    Attributes:
        passphrase: User-chosen passphrase (min 8 characters) used to derive
            the AES-256-GCM encryption key via Argon2id.
    """

    passphrase: str = Field(min_length=8)


class EncryptionActionResponse(BaseModel):
    """Schema for encryption action responses (setup, unlock).

    Attributes:
        ok: Always True on success.
    """

    ok: bool = True


# ── WebAuthn schemas ──────────────────────────────────────────────────────────


class WebAuthnRegistrationBeginResponse(BaseModel):
    """Options returned to the browser to initiate credential registration."""

    options: dict[str, object]


class WebAuthnRegistrationCompleteRequest(BaseModel):
    """Attestation response from the browser after credential creation.

    Attributes:
        credential: The JSON-serialised ``PublicKeyCredential`` object.
        name: Optional human-readable name for this credential (e.g. "iPhone 15").
    """

    credential: dict[str, object]
    name: str | None = None


class WebAuthnAuthBeginRequest(BaseModel):
    """Username sent to the server to start a WebAuthn authentication flow.

    Attributes:
        username: The user's account username.
    """

    username: str


class WebAuthnAuthBeginResponse(BaseModel):
    """Challenge options returned to the browser to initiate authentication."""

    options: dict[str, object]


class WebAuthnAuthCompleteRequest(BaseModel):
    """Assertion response from the browser after challenge signing.

    Attributes:
        credential: The JSON-serialised ``PublicKeyCredential`` assertion.
    """

    credential: dict[str, object]


class WebAuthnCredentialRead(BaseModel):
    """Read schema for a registered WebAuthn credential.

    Attributes:
        id: Primary key.
        name: Human-readable label.
        created_at: Registration timestamp (ISO string).
    """

    id: int
    name: str | None
    created_at: str

    model_config = {"from_attributes": True}
