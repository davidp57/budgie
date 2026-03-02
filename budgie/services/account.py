"""Account CRUD service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.account import Account
from budgie.schemas.account import AccountCreate, AccountUpdate


async def get_accounts(db: AsyncSession, user_id: int) -> list[Account]:
    """Return all accounts owned by the given user.

    Args:
        db: Async database session.
        user_id: Owner user ID.

    Returns:
        List of Account instances.
    """
    result = await db.execute(select(Account).where(Account.user_id == user_id))
    return list(result.scalars().all())


async def get_account(
    db: AsyncSession, account_id: int, user_id: int
) -> Account | None:
    """Fetch a single account by ID, scoped to the user.

    Args:
        db: Async database session.
        account_id: Account primary key.
        user_id: Owner user ID for authorization.

    Returns:
        Account if found and owned by the user, None otherwise.
    """
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_account(
    db: AsyncSession, schema: AccountCreate, user_id: int
) -> Account:
    """Create a new account for the given user.

    Args:
        db: Async database session.
        schema: Validated account creation schema.
        user_id: Owner user ID.

    Returns:
        Newly created Account instance.
    """
    account = Account(
        user_id=user_id,
        name=schema.name,
        account_type=schema.account_type,
        on_budget=schema.on_budget,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


async def update_account(
    db: AsyncSession, account: Account, schema: AccountUpdate
) -> Account:
    """Partially update an account.

    Args:
        db: Async database session.
        account: Existing Account instance to update.
        schema: Partial update schema.

    Returns:
        Updated Account instance.
    """
    for field, value in schema.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    await db.commit()
    await db.refresh(account)
    return account


async def delete_account(db: AsyncSession, account: Account) -> None:
    """Delete an account.

    Args:
        db: Async database session.
        account: Account instance to delete.
    """
    await db.delete(account)
    await db.commit()
