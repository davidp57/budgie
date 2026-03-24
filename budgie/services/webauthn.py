"""WebAuthn (Passkeys) service.

Wraps the ``webauthn`` library to handle credential registration and
authentication.  The relying-party origin and ID are loaded from settings.

State (pending challenges) is held in-process RAM keyed by ``user_id``.
For a single-user NAS deployment this is acceptable; a Redis cache would
be needed for multi-process setups.
"""

import base64
import json
import threading

import webauthn
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from budgie.config import settings

# ── In-process challenge cache (user_id → bytes) ──────────────────────────

_challenges: dict[int, bytes] = {}
_challenge_lock = threading.Lock()


def _set_challenge(user_id: int, challenge: bytes) -> None:
    with _challenge_lock:
        _challenges[user_id] = challenge


def _pop_challenge(user_id: int) -> bytes | None:
    with _challenge_lock:
        return _challenges.pop(user_id, None)


def _b64url_encode(data: bytes) -> str:
    """URL-safe base64 encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


# ── Registration ─────────────────────────────────────────────────────────────


def begin_registration(
    user_id: int,
    username: str,
    existing_credential_ids: list[bytes],
) -> dict[str, object]:
    """Generate WebAuthn registration options for a user.

    Args:
        user_id: Numeric user ID (used as WebAuthn user handle).
        username: Display name shown on the authenticator.
        existing_credential_ids: Already-registered credential IDs to exclude.

    Returns:
        JSON-serialisable options dict to send to the browser.
    """
    exclude = [PublicKeyCredentialDescriptor(id=cid) for cid in existing_credential_ids]
    options = webauthn.generate_registration_options(
        rp_id=settings.webauthn_rp_id,
        rp_name=settings.webauthn_rp_name,
        user_id=str(user_id).encode(),
        user_name=username,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        exclude_credentials=exclude,
    )
    _set_challenge(user_id, options.challenge)
    result: dict[str, object] = json.loads(webauthn.options_to_json(options))
    return result


def complete_registration(
    user_id: int,
    credential: dict[str, object],
) -> tuple[bytes, bytes, int]:
    """Verify a registration attestation response from the browser.

    Args:
        user_id: The user being registered.
        credential: The ``PublicKeyCredential`` JSON from the browser.

    Returns:
        Tuple of ``(credential_id, public_key, sign_count)``.

    Raises:
        ValueError: If the challenge is missing, expired or verification fails.
    """
    challenge = _pop_challenge(user_id)
    if challenge is None:
        raise ValueError("No pending registration challenge for this user.")

    verified = webauthn.verify_registration_response(
        credential=json.dumps(credential),
        expected_challenge=challenge,
        expected_rp_id=settings.webauthn_rp_id,
        expected_origin=settings.webauthn_origin,
        require_user_verification=False,
    )
    return (
        verified.credential_id,
        verified.credential_public_key,
        verified.sign_count,
    )


# ── Authentication ────────────────────────────────────────────────────────────


def begin_authentication(
    user_id: int,
    credential_ids: list[bytes],
) -> dict[str, object]:
    """Generate WebAuthn authentication options for a user.

    Args:
        user_id: The user attempting to log in.
        credential_ids: The user's registered credential IDs.

    Returns:
        JSON-serialisable options dict to send to the browser.
    """
    allow = [PublicKeyCredentialDescriptor(id=cid) for cid in credential_ids]
    options = webauthn.generate_authentication_options(
        rp_id=settings.webauthn_rp_id,
        allow_credentials=allow,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    _set_challenge(user_id, options.challenge)
    result: dict[str, object] = json.loads(webauthn.options_to_json(options))
    return result


def complete_authentication(
    user_id: int,
    credential: dict[str, object],
    stored_public_key: bytes,
    stored_sign_count: int,
) -> int:
    """Verify a WebAuthn authentication assertion from the browser.

    Args:
        user_id: The user authenticating.
        credential: The ``PublicKeyCredential`` assertion JSON from the browser.
        stored_public_key: The public key bytes stored at registration time.
        stored_sign_count: The sign counter stored at registration time.

    Returns:
        The new sign count to persist.

    Raises:
        ValueError: If the challenge is missing, expired or verification fails.
    """
    challenge = _pop_challenge(user_id)
    if challenge is None:
        raise ValueError("No pending authentication challenge for this user.")

    verified = webauthn.verify_authentication_response(
        credential=json.dumps(credential),
        expected_challenge=challenge,
        expected_rp_id=settings.webauthn_rp_id,
        expected_origin=settings.webauthn_origin,
        credential_public_key=stored_public_key,
        credential_current_sign_count=stored_sign_count,
        require_user_verification=False,
    )
    new_count: int = verified.new_sign_count
    return new_count
