"""Data migration service: encrypt existing plaintext user data.

Called once when a user sets up encryption for the first time.  All
transactions (memo field) and payees (name field) belonging to the user
are encrypted with their freshly derived AES-256-GCM key in a single
database transaction — rollback on any error ensures atomicity.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.account import Account
from budgie.models.payee import Payee
from budgie.models.transaction import Transaction
from budgie.models.user import User
from budgie.services.crypto import InvalidKeyError, decrypt_field, encrypt_field


async def encrypt_user_data(db: AsyncSession, user_id: int, key: bytes) -> None:
    """Encrypt all plaintext user data with the given AES-256-GCM key.

    This function is idempotent: fields that are already encrypted (i.e.
    successfully decryptable with the given key) are skipped, preventing
    double-encryption on retry.

    Encrypts in-place (within the same database session) and commits once
    at the end.  If any error occurs, the caller's session will not be
    committed and the database will remain unchanged.

    Also sets ``User.fields_encrypted = True`` to mark that the field-level
    migration has been completed.  This flag is distinct from
    ``User.is_encrypted``, which only indicates that encryption has been
    *configured* for an account.

    Encrypted fields:
    - ``Transaction.memo`` (all transactions across all user accounts)
    - ``Payee.name`` (all payees belonging to the user)

    Args:
        db: Async database session (must be open and active).
        user_id: Primary key of the user whose data to encrypt.
        key: 32-byte AES-256-GCM encryption key.
    """
    # ── Transactions ──────────────────────────────────────────────────────────
    txn_result = await db.execute(
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(Account.user_id == user_id)
    )
    for txn in txn_result.scalars().all():
        if txn.memo is not None:
            try:
                decrypt_field(txn.memo, key)
                # Already encrypted — skip to avoid double-encryption.
            except InvalidKeyError:
                txn.memo = encrypt_field(txn.memo, key)

    # ── Payees ──────────────────────────────────────────────────────────────────
    payee_result = await db.execute(select(Payee).where(Payee.user_id == user_id))
    for payee in payee_result.scalars().all():
        try:
            decrypt_field(payee.name, key)
            # Already encrypted — skip.
        except InvalidKeyError:
            payee.name = encrypt_field(payee.name, key)

    # ── Mark migration as done ────────────────────────────────────────────────
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is not None:
        user.fields_encrypted = True

    await db.commit()
