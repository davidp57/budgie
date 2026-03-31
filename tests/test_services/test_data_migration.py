"""Tests for the data_migration service (encrypt_user_data)."""

import datetime

import pytest
from budgie.models.account import Account
from budgie.models.payee import Payee
from budgie.models.transaction import Transaction
from budgie.models.user import User
from budgie.services.crypto import decrypt_field, encrypt_field
from budgie.services.data_migration import encrypt_user_data
from sqlalchemy.ext.asyncio import AsyncSession

# -- Constants -----------------------------------------------------------------

# Use a fixed 32-byte key to avoid slow Argon2id key derivation at module load.
KEY = b"\x42" * 32


# -- Helpers -------------------------------------------------------------------


async def _make_user(db: AsyncSession, username: str = "alice") -> User:
    user = User(username=username, hashed_password="x", is_encrypted=False)
    db.add(user)
    await db.flush()
    return user


async def _make_account(db: AsyncSession, user_id: int) -> Account:
    account = Account(
        user_id=user_id,
        name="Main",
        account_type="checking",
        on_budget=True,
    )
    db.add(account)
    await db.flush()
    return account


# -- Tests ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_encrypt_user_data_encrypts_transaction_memos(
    db_session: AsyncSession,
) -> None:
    """Transaction memos must be stored as encrypted blobs after migration."""
    user = await _make_user(db_session)
    account = await _make_account(db_session, user.id)
    txn = Transaction(
        account_id=account.id,
        date=datetime.date(2024, 1, 15),
        amount=-5000,
        memo="Plaintext memo",
    )
    db_session.add(txn)
    await db_session.commit()
    await db_session.refresh(txn)

    await encrypt_user_data(db_session, user.id, KEY)

    await db_session.refresh(txn)
    assert txn.memo is not None
    assert txn.memo != "Plaintext memo"
    assert decrypt_field(txn.memo, KEY) == "Plaintext memo"


@pytest.mark.asyncio
async def test_encrypt_user_data_encrypts_payee_names(
    db_session: AsyncSession,
) -> None:
    """Payee names must be stored as encrypted blobs after migration."""
    user = await _make_user(db_session)
    payee = Payee(user_id=user.id, name="Plaintext payee")
    db_session.add(payee)
    await db_session.commit()
    await db_session.refresh(payee)

    await encrypt_user_data(db_session, user.id, KEY)

    await db_session.refresh(payee)
    assert payee.name != "Plaintext payee"
    assert decrypt_field(payee.name, KEY) == "Plaintext payee"


@pytest.mark.asyncio
async def test_encrypt_user_data_skips_none_memos(
    db_session: AsyncSession,
) -> None:
    """Transactions with memo=None must remain None after migration."""
    user = await _make_user(db_session)
    account = await _make_account(db_session, user.id)
    txn = Transaction(
        account_id=account.id,
        date=datetime.date(2024, 2, 1),
        amount=-1000,
        memo=None,
    )
    db_session.add(txn)
    await db_session.commit()
    await db_session.refresh(txn)

    await encrypt_user_data(db_session, user.id, KEY)

    await db_session.refresh(txn)
    assert txn.memo is None


@pytest.mark.asyncio
async def test_encrypt_user_data_does_not_affect_other_users(
    db_session: AsyncSession,
) -> None:
    """Data belonging to another user must not be encrypted."""
    alice = await _make_user(db_session, "alice")
    bob = await _make_user(db_session, "bob")

    alice_account = await _make_account(db_session, alice.id)
    bob_account = await _make_account(db_session, bob.id)

    bob_txn = Transaction(
        account_id=bob_account.id,
        date=datetime.date(2024, 3, 1),
        amount=-2000,
        memo="Bob memo",
    )
    bob_payee = Payee(user_id=bob.id, name="Bob payee")
    alice_txn = Transaction(
        account_id=alice_account.id,
        date=datetime.date(2024, 3, 1),
        amount=-1000,
        memo="Alice memo",
    )
    alice_payee = Payee(user_id=alice.id, name="Alice payee")
    db_session.add_all([bob_txn, bob_payee, alice_txn, alice_payee])
    await db_session.commit()

    # Encrypt only alice's data
    await encrypt_user_data(db_session, alice.id, KEY)

    await db_session.refresh(bob_txn)
    await db_session.refresh(bob_payee)
    assert bob_txn.memo == "Bob memo"
    assert bob_payee.name == "Bob payee"


@pytest.mark.asyncio
async def test_encrypt_user_data_sets_fields_encrypted_flag(
    db_session: AsyncSession,
) -> None:
    """User.fields_encrypted must be True after migration."""
    user = await _make_user(db_session, "charlie")
    await db_session.commit()

    await encrypt_user_data(db_session, user.id, KEY)

    await db_session.refresh(user)
    assert user.fields_encrypted is True


@pytest.mark.asyncio
async def test_encrypt_user_data_is_idempotent(
    db_session: AsyncSession,
) -> None:
    """Running encrypt_user_data twice must not double-encrypt the data."""
    user = await _make_user(db_session, "diana")
    account = await _make_account(db_session, user.id)
    txn = Transaction(
        account_id=account.id,
        date=datetime.date(2024, 5, 1),
        amount=-3000,
        memo="Idempotent memo",
    )
    payee = Payee(user_id=user.id, name="Idempotent payee")
    db_session.add_all([txn, payee])
    await db_session.commit()

    # First migration
    await encrypt_user_data(db_session, user.id, KEY)
    await db_session.refresh(txn)
    await db_session.refresh(payee)
    memo_after_first = txn.memo
    payee_name_after_first = payee.name
    assert memo_after_first is not None
    assert payee_name_after_first is not None

    # Second migration — must be a no-op
    await encrypt_user_data(db_session, user.id, KEY)
    await db_session.refresh(txn)
    await db_session.refresh(payee)

    # Blobs must be the same length and still decrypt correctly.
    assert txn.memo is not None
    assert payee.name is not None
    assert len(txn.memo) == len(memo_after_first)  # no extra wrapping
    assert decrypt_field(txn.memo, KEY) == "Idempotent memo"
    assert decrypt_field(payee.name, KEY) == "Idempotent payee"
    # Verify stored blob did not change (idempotent means same ciphertext)
    assert txn.memo == memo_after_first
    assert payee.name == payee_name_after_first


@pytest.mark.asyncio
async def test_encrypt_user_data_already_encrypted_field_is_skipped(
    db_session: AsyncSession,
) -> None:
    """A memo that is already encrypted must not be re-encrypted."""
    user = await _make_user(db_session, "eve")
    account = await _make_account(db_session, user.id)
    already_encrypted = encrypt_field("Pre-encrypted", KEY)
    txn = Transaction(
        account_id=account.id,
        date=datetime.date(2024, 6, 1),
        amount=-500,
        memo=already_encrypted,
    )
    db_session.add(txn)
    await db_session.commit()

    await encrypt_user_data(db_session, user.id, KEY)

    await db_session.refresh(txn)
    # Blob must still decrypt to the original plaintext (not double-encrypted).
    assert txn.memo is not None
    assert decrypt_field(txn.memo, KEY) == "Pre-encrypted"
