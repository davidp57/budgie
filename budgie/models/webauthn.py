"""WebAuthn credential ORM model."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from budgie.database import Base

if TYPE_CHECKING:
    from budgie.models.user import User


class WebAuthnCredential(Base):
    """Stores a single WebAuthn (Passkey) credential for a user.

    One user may register multiple credentials (e.g. phone + laptop).

    Attributes:
        id: Primary key.
        user_id: Owner of the credential.
        credential_id: Raw bytes of the credential ID returned by the authenticator.
        public_key: COSE-encoded public key bytes.
        sign_count: Authenticator sign counter (replay protection).
        transports: JSON-encoded list of transports (e.g. ``["internal"]``).
        name: Optional human-readable name for the credential.
        created_at: Registration timestamp.
    """

    __tablename__ = "webauthn_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    credential_id: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False, unique=True
    )
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transports: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="webauthn_credentials")
