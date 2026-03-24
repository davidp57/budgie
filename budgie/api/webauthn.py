"""WebAuthn (Passkeys) authentication router.

Provides endpoints for registering and using passkeys as an alternative
to username/password login.

Registration requires an authenticated session (the user must be logged in
with their password first).  Authentication is public: the passkey replaces
the password step and issues a new JWT on success.
"""

import base64

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from budgie.api.deps import CurrentUser, DBSession
from budgie.models.webauthn import WebAuthnCredential
from budgie.schemas.auth import (
    EncryptionActionResponse,
    TokenResponse,
    WebAuthnAuthBeginRequest,
    WebAuthnAuthBeginResponse,
    WebAuthnAuthCompleteRequest,
    WebAuthnCredentialRead,
    WebAuthnRegistrationBeginResponse,
    WebAuthnRegistrationCompleteRequest,
)
from budgie.services import webauthn as webauthn_service
from budgie.services.auth import create_access_token
from budgie.services.user import get_user_by_id, get_user_by_username

router = APIRouter(prefix="/api/auth/webauthn", tags=["webauthn"])


# ── Registration (requires authenticated session) ─────────────────────────────


@router.post("/register/begin", response_model=WebAuthnRegistrationBeginResponse)
async def register_begin(
    current_user: CurrentUser,
    db: DBSession,
) -> WebAuthnRegistrationBeginResponse:
    """Start WebAuthn credential registration for the current user.

    Args:
        current_user: Authenticated user from JWT.
        db: Async database session.

    Returns:
        PublicKeyCredentialCreationOptions to pass to browser's
        ``navigator.credentials.create()``.
    """
    result = await db.execute(
        select(WebAuthnCredential).where(WebAuthnCredential.user_id == current_user.id)
    )
    existing_ids = [c.credential_id for c in result.scalars().all()]
    options = webauthn_service.begin_registration(
        current_user.id, current_user.username, existing_ids
    )
    return WebAuthnRegistrationBeginResponse(options=options)


@router.post(
    "/register/complete",
    response_model=WebAuthnCredentialRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_complete(
    schema: WebAuthnRegistrationCompleteRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> WebAuthnCredentialRead:
    """Verify attestation and persist the new WebAuthn credential.

    Args:
        schema: Credential from ``navigator.credentials.create()`` + optional name.
        current_user: Authenticated user from JWT.
        db: Async database session.

    Returns:
        The saved credential read schema.

    Raises:
        HTTPException: 400 if verification fails or challenge is expired.
    """
    try:
        credential_id, public_key, sign_count = webauthn_service.complete_registration(
            current_user.id, schema.credential
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    cred = WebAuthnCredential(
        user_id=current_user.id,
        credential_id=credential_id,
        public_key=public_key,
        sign_count=sign_count,
        name=schema.name,
    )
    db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return WebAuthnCredentialRead(
        id=cred.id,
        name=cred.name,
        created_at=cred.created_at.isoformat(),
    )


# ── Credential management ─────────────────────────────────────────────────────


@router.get("/credentials", response_model=list[WebAuthnCredentialRead])
async def list_credentials(
    current_user: CurrentUser,
    db: DBSession,
) -> list[WebAuthnCredentialRead]:
    """List all registered passkeys for the current user.

    Args:
        current_user: Authenticated user from JWT.
        db: Async database session.

    Returns:
        List of credential read schemas ordered by registration date.
    """
    result = await db.execute(
        select(WebAuthnCredential)
        .where(WebAuthnCredential.user_id == current_user.id)
        .order_by(WebAuthnCredential.created_at)
    )
    return [
        WebAuthnCredentialRead(
            id=c.id, name=c.name, created_at=c.created_at.isoformat()
        )
        for c in result.scalars().all()
    ]


@router.delete(
    "/credentials/{credential_db_id}",
    response_model=EncryptionActionResponse,
)
async def delete_credential(
    credential_db_id: int,
    current_user: CurrentUser,
    db: DBSession,
) -> EncryptionActionResponse:
    r"""Delete a registered passkey.

    Args:
        credential_db_id: Database primary key of the credential to remove.
        current_user: Authenticated user from JWT.
        db: Async database session.

    Returns:
        ``{"ok": true}`` on success.

    Raises:
        HTTPException: 404 if the credential is not found or belongs to another user.
    """
    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.id == credential_db_id,
            WebAuthnCredential.user_id == current_user.id,
        )
    )
    cred = result.scalar_one_or_none()
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )
    await db.delete(cred)
    await db.commit()
    return EncryptionActionResponse()


# ── Authentication (public — no JWT required) ─────────────────────────────────


@router.post("/authenticate/begin", response_model=WebAuthnAuthBeginResponse)
async def authenticate_begin(
    schema: WebAuthnAuthBeginRequest,
    db: DBSession,
) -> WebAuthnAuthBeginResponse:
    """Start WebAuthn authentication for the given username.

    Args:
        schema: Username identifying the user.
        db: Async database session.

    Returns:
        PublicKeyCredentialRequestOptions to pass to browser's
        ``navigator.credentials.get()``.

    Raises:
        HTTPException: 404 if the user does not exist or has no credentials.
    """
    user = await get_user_by_username(db, schema.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    result = await db.execute(
        select(WebAuthnCredential).where(WebAuthnCredential.user_id == user.id)
    )
    credential_ids = [c.credential_id for c in result.scalars().all()]
    if not credential_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No passkeys registered for this user",
        )
    options = webauthn_service.begin_authentication(user.id, credential_ids)
    return WebAuthnAuthBeginResponse(options=options)


@router.post("/authenticate/complete", response_model=TokenResponse)
async def authenticate_complete(
    schema: WebAuthnAuthCompleteRequest,
    db: DBSession,
) -> TokenResponse:
    """Verify WebAuthn assertion and issue a JWT on success.

    The user is identified by looking up the credential ID in the database.

    Args:
        schema: Credential assertion from ``navigator.credentials.get()``.
        db: Async database session.

    Returns:
        JWT token response identical to the password login endpoint.

    Raises:
        HTTPException: 401 if the assertion is invalid.
        HTTPException: 404 if the credential ID is unknown.
    """
    # Decode the credential ID from the browser response (base64url, no padding)
    raw_id_b64: object = schema.credential.get("rawId") or schema.credential.get("id")
    if not isinstance(raw_id_b64, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing credential id in assertion",
        )
    # Add padding if needed
    padding = 4 - len(raw_id_b64) % 4
    if padding != 4:
        raw_id_b64 += "=" * padding
    try:
        raw_id = base64.urlsafe_b64decode(raw_id_b64)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credential id encoding",
        ) from exc

    result = await db.execute(
        select(WebAuthnCredential).where(WebAuthnCredential.credential_id == raw_id)
    )
    cred = result.scalar_one_or_none()
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown passkey",
        )

    try:
        new_sign_count = webauthn_service.complete_authentication(
            user_id=cred.user_id,
            credential=schema.credential,
            stored_public_key=cred.public_key,
            stored_sign_count=cred.sign_count,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    # Persist the updated sign counter
    cred.sign_count = new_sign_count
    await db.commit()

    # Load the user to build the JWT
    user = await get_user_by_id(db, cred.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User not found after credential lookup",
        )

    token = create_access_token({"sub": user.username})
    return TokenResponse(
        access_token=token,
        needs_encryption_setup=not user.is_encrypted,
        is_encrypted=user.is_encrypted,
    )
