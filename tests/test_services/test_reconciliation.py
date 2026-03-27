"""Tests for the reconciliation service."""

import datetime

import pytest
from budgie.models.account import Account
from budgie.models.category import Category, CategoryGroup
from budgie.models.category_rule import CategoryRule
from budgie.models.transaction import Transaction
from budgie.models.user import User
from budgie.services import reconciliation as svc
from budgie.services.reconciliation import _extract_rule_pattern, _matches_rule
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(db: AsyncSession) -> User:
    user = User(username="alice", hashed_password="x")
    db.add(user)
    await db.flush()
    return user


async def _create_account(db: AsyncSession, user_id: int) -> Account:
    account = Account(
        user_id=user_id,
        name="Checking",
        account_type="checking",
        on_budget=True,
    )
    db.add(account)
    await db.flush()
    return account


async def _create_category(
    db: AsyncSession, user_id: int, name: str = "Food"
) -> Category:
    group = CategoryGroup(user_id=user_id, name="Living")
    db.add(group)
    await db.flush()
    cat = Category(group_id=group.id, name=name)
    db.add(cat)
    await db.flush()
    return cat


def _bank_tx(
    account_id: int,
    amount: int,
    date: datetime.date | None = None,
    label: str = "CARREFOUR",
) -> Transaction:
    return Transaction(
        account_id=account_id,
        date=date or datetime.date(2026, 3, 10),
        amount=amount,
        memo=label,
        status="real",
        import_hash=f"hash-{label}-{amount}",
    )


def _expense(
    account_id: int,
    amount: int,
    category_id: int | None = None,
    date: datetime.date | None = None,
    label: str = "Courses",
    status: str = "real",
) -> Transaction:
    return Transaction(
        account_id=account_id,
        date=date or datetime.date(2026, 3, 10),
        amount=amount,
        memo=label,
        category_id=category_id,
        status=status,
        import_hash=None,
    )


# ---------------------------------------------------------------------------
# get_view
# ---------------------------------------------------------------------------


async def test_get_view_separates_bank_and_budget(db_session: AsyncSession) -> None:
    """Bank txs (import_hash set) and budget txs are returned separately."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)

    bank = _bank_tx(acc.id, -5230)
    exp = _expense(acc.id, -5000)
    db_session.add_all([bank, exp])
    await db_session.commit()

    view = await svc.get_view(db_session, user.id, acc.id, "2026-03")

    assert len(view.bank_txs) == 1
    assert view.bank_txs[0].id == bank.id
    assert len(view.expenses) == 1
    assert view.expenses[0].id == exp.id
    assert view.links == []


async def test_get_view_month_filter(db_session: AsyncSession) -> None:
    """Only transactions in the requested month are included."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)

    march = _bank_tx(acc.id, -1000, date=datetime.date(2026, 3, 5))
    april = _bank_tx(acc.id, -2000, date=datetime.date(2026, 4, 1), label="LECLERC")
    db_session.add_all([march, april])
    await db_session.commit()

    view = await svc.get_view(db_session, user.id, acc.id, "2026-03")

    assert len(view.bank_txs) == 1
    assert view.bank_txs[0].id == march.id


async def test_get_view_shows_links(db_session: AsyncSession) -> None:
    """A linked pair is reflected in view.links."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)

    bank = _bank_tx(acc.id, -5230)
    exp = _expense(acc.id, -5000)
    db_session.add_all([bank, exp])
    await db_session.flush()
    exp.reconciled_with_id = bank.id
    await db_session.commit()

    view = await svc.get_view(db_session, user.id, acc.id, "2026-03")

    assert len(view.links) == 1
    assert view.links[0].bank_tx_id == bank.id
    assert view.links[0].expense_id == exp.id


# ---------------------------------------------------------------------------
# link
# ---------------------------------------------------------------------------


async def test_link_sets_reconciled_with_id(db_session: AsyncSession) -> None:
    """Linking sets expense.reconciled_with_id to the bank tx id."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)

    bank = _bank_tx(acc.id, -5230)
    exp = _expense(acc.id, -5000)
    db_session.add_all([bank, exp])
    await db_session.commit()

    from budgie.schemas.reconciliation import LinkRequest

    req = LinkRequest(bank_tx_id=bank.id, expense_id=exp.id, adjust_amount=False)
    link = await svc.link(db_session, user.id, req)

    await db_session.refresh(exp)
    assert exp.reconciled_with_id == bank.id
    assert link.bank_tx_id == bank.id
    assert link.expense_id == exp.id


async def test_link_adjusts_amount(db_session: AsyncSession) -> None:
    """adjust_amount=True updates the expense amount to match the bank tx."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)

    bank = _bank_tx(acc.id, -5230)
    exp = _expense(acc.id, -5000)
    db_session.add_all([bank, exp])
    await db_session.commit()

    from budgie.schemas.reconciliation import LinkRequest

    req = LinkRequest(bank_tx_id=bank.id, expense_id=exp.id, adjust_amount=True)
    await svc.link(db_session, user.id, req)

    await db_session.refresh(exp)
    assert exp.amount == -5230


async def test_link_sets_memo(db_session: AsyncSession) -> None:
    """A memo provided in the request is stored on the expense."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)

    bank = _bank_tx(acc.id, -1000)
    exp = _expense(acc.id, -1000)
    db_session.add_all([bank, exp])
    await db_session.commit()

    from budgie.schemas.reconciliation import LinkRequest

    req = LinkRequest(bank_tx_id=bank.id, expense_id=exp.id, memo="Carrefour Metz")
    await svc.link(db_session, user.id, req)

    await db_session.refresh(exp)
    assert exp.memo == "Carrefour Metz"


async def test_link_raises_if_already_linked(db_session: AsyncSession) -> None:
    """Cannot link a bank tx that already has a link."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)

    bank = _bank_tx(acc.id, -1000)
    exp1 = _expense(acc.id, -1000, label="Exp1")
    exp2 = _expense(acc.id, -900, label="Exp2")
    db_session.add_all([bank, exp1, exp2])
    await db_session.flush()
    exp1.reconciled_with_id = bank.id
    await db_session.commit()

    from budgie.schemas.reconciliation import LinkRequest

    with pytest.raises(ValueError, match="already linked"):
        await svc.link(
            db_session, user.id, LinkRequest(bank_tx_id=bank.id, expense_id=exp2.id)
        )


async def test_link_raises_on_wrong_user(db_session: AsyncSession) -> None:
    """Cannot link transactions belonging to another user."""
    user1 = await _create_user(db_session)
    user2 = User(username="bob", hashed_password="y")
    db_session.add(user2)
    await db_session.flush()

    acc1 = await _create_account(db_session, user1.id)
    bank = _bank_tx(acc1.id, -1000)
    exp = _expense(acc1.id, -1000)
    db_session.add_all([bank, exp])
    await db_session.commit()

    from budgie.schemas.reconciliation import LinkRequest

    with pytest.raises(ValueError, match="not found"):
        await svc.link(
            db_session,
            user2.id,
            LinkRequest(bank_tx_id=bank.id, expense_id=exp.id),
        )


# ---------------------------------------------------------------------------
# unlink
# ---------------------------------------------------------------------------


async def test_unlink_clears_reconciled_with_id(db_session: AsyncSession) -> None:
    """Unlinking sets reconciled_with_id back to None."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)

    bank = _bank_tx(acc.id, -1000)
    exp = _expense(acc.id, -1000)
    db_session.add_all([bank, exp])
    await db_session.flush()
    exp.reconciled_with_id = bank.id
    await db_session.commit()

    await svc.unlink(db_session, user.id, bank_tx_id=bank.id)

    await db_session.refresh(exp)
    assert exp.reconciled_with_id is None


# ---------------------------------------------------------------------------
# get_suggestions
# ---------------------------------------------------------------------------


async def test_suggestions_match_by_category(db_session: AsyncSession) -> None:
    """A bank tx with a matching category rule is paired with the closest expense."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)
    cat = await _create_category(db_session, user.id, "Food")

    rule = CategoryRule(
        user_id=user.id,
        pattern="carrefour",
        match_field="payee",
        match_type="contains",
        category_id=cat.id,
        priority=10,
    )
    db_session.add(rule)

    bank = _bank_tx(acc.id, -5230, label="CARREFOUR METZ")
    exp_close = _expense(acc.id, -5000, category_id=cat.id, label="Courses")
    exp_far = _expense(acc.id, -2000, category_id=cat.id, label="Autre")
    db_session.add_all([bank, exp_close, exp_far])
    await db_session.commit()

    suggestions = await svc.get_suggestions(db_session, user.id, acc.id, "2026-03")

    assert len(suggestions) == 1
    assert suggestions[0].bank_tx.id == bank.id
    assert suggestions[0].expense.id == exp_close.id


async def test_suggestions_ignore_already_linked(db_session: AsyncSession) -> None:
    """Already-linked pairs are excluded from suggestions."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)
    cat = await _create_category(db_session, user.id, "Food")

    rule = CategoryRule(
        user_id=user.id,
        pattern="carrefour",
        match_field="payee",
        match_type="contains",
        category_id=cat.id,
        priority=10,
    )
    db_session.add(rule)

    bank = _bank_tx(acc.id, -5230, label="CARREFOUR METZ")
    exp = _expense(acc.id, -5000, category_id=cat.id)
    db_session.add_all([bank, exp])
    await db_session.flush()
    exp.reconciled_with_id = bank.id
    await db_session.commit()

    suggestions = await svc.get_suggestions(db_session, user.id, acc.id, "2026-03")

    assert suggestions == []


# ---------------------------------------------------------------------------
# _build_rule_matches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_matches_returned_when_no_expense(db_session: AsyncSession) -> None:
    """A bank tx matched by a rule but with no existing expense → rule_matches."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)
    cat = await _create_category(db_session, user.id, "Streaming")

    db_session.add(
        CategoryRule(
            user_id=user.id,
            pattern="netflix",
            match_field="memo",
            match_type="contains",
            category_id=cat.id,
            priority=10,
        )
    )
    bank = _bank_tx(acc.id, -1599, label="CARTE 01/03/26 NETFLIX.COM CB*1234")
    db_session.add(bank)
    await db_session.commit()

    view = await svc.get_view(db_session, user.id, acc.id, "2026-03")

    assert len(view.suggestions) == 0
    assert len(view.rule_matches) == 1
    rm = view.rule_matches[0]
    assert rm.bank_tx.id == bank.id
    assert rm.category_id == cat.id
    assert rm.category_name == "Streaming"


@pytest.mark.asyncio
async def test_rule_matches_excluded_when_suggestion_exists(
    db_session: AsyncSession,
) -> None:
    """A bank tx already promoted to a suggestion must not appear in rule_matches."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)
    cat = await _create_category(db_session, user.id, "Streaming")

    db_session.add(
        CategoryRule(
            user_id=user.id,
            pattern="netflix",
            match_field="memo",
            match_type="contains",
            category_id=cat.id,
            priority=10,
        )
    )
    bank = _bank_tx(acc.id, -1599, label="CARTE 01/03/26 NETFLIX.COM CB*1234")
    exp = _expense(acc.id, -1599, category_id=cat.id)
    db_session.add_all([bank, exp])
    await db_session.commit()

    view = await svc.get_view(db_session, user.id, acc.id, "2026-03")

    # The pair should be in suggestions, not in rule_matches
    assert len(view.suggestions) == 1
    assert len(view.rule_matches) == 0


@pytest.mark.asyncio
async def test_rule_matches_excluded_when_linked(db_session: AsyncSession) -> None:
    """A bank tx that is already linked must not appear in rule_matches."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)
    cat = await _create_category(db_session, user.id, "Streaming")

    db_session.add(
        CategoryRule(
            user_id=user.id,
            pattern="netflix",
            match_field="memo",
            match_type="contains",
            category_id=cat.id,
            priority=10,
        )
    )
    bank = _bank_tx(acc.id, -1599, label="CARTE 01/03/26 NETFLIX.COM CB*1234")
    exp = _expense(acc.id, -1599, category_id=cat.id)
    db_session.add_all([bank, exp])
    await db_session.flush()
    exp.reconciled_with_id = bank.id
    await db_session.commit()

    view = await svc.get_view(db_session, user.id, acc.id, "2026-03")

    assert len(view.rule_matches) == 0


# ---------------------------------------------------------------------------
# cloture
# ---------------------------------------------------------------------------


async def test_cloture_reconciles_linked_pairs(db_session: AsyncSession) -> None:
    """Clôture sets both linked txs to 'reconciled'."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)

    bank = _bank_tx(acc.id, -1000)
    exp = _expense(acc.id, -1000)
    db_session.add_all([bank, exp])
    await db_session.flush()
    exp.reconciled_with_id = bank.id
    await db_session.commit()

    from budgie.schemas.reconciliation import ClotureRequest

    result = await svc.cloture(
        db_session, user.id, ClotureRequest(account_id=acc.id, month="2026-03")
    )

    await db_session.refresh(bank)
    await db_session.refresh(exp)
    assert bank.status == "reconciled"
    assert exp.status == "reconciled"
    assert result.reconciled_count == 1
    assert result.linked_count == 1


# ---------------------------------------------------------------------------
# _extract_rule_pattern — unit tests (pure function, no DB needed)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "memo, expected",
    [
        # Card transaction with date and card fragment
        ("CARTE 23/03/26 STEAMGAMES.COM 42 CB*6338", "STEAMGAMES.COM"),
        # AVOIR (credit/refund) prefix stripped — date removed too
        ("AVOIR 23/03/26 STEAMGAMES.COM 42 CB*6338", "STEAMGAMES.COM"),
        # AVOIR CB variant
        ("AVOIR CB 23/03/26 STEAMGAMES.COM", "STEAMGAMES.COM"),
        # VIR SEPA with useful label
        ("VIR SEPA LOYER APPARTEMENT", "LOYER APPARTEMENT"),
        # PRLV with serial number at the end
        ("PRLV SEPA EDF CONTRAT 12345678", "EDF CONTRAT"),
        # Compact date variant
        ("CARTE 230326 NETFLIX.COM CB*1234", "NETFLIX.COM"),
        # ACHAT CB INTERNET
        ("ACHAT CB INTERNET AMAZON EU 12/03/26", "AMAZON EU"),
        # Already clean
        ("CARREFOUR CITY PARIS", "CARREFOUR CITY PARIS"),
        # Only a date + noise → returns None
        ("RETRAIT DAB 23/03/26 75001", None),
        # Empty string → None
        ("", None),
        # Only numbers → None
        ("12345 67890", None),
        # Preserve domain-style names
        ("CARTE 01/01/26 SPOTIFY.COM 9 CB*0001", "SPOTIFY.COM"),
    ],
)
def test_extract_rule_pattern(memo: str, expected: str | None) -> None:
    """_extract_rule_pattern should return a clean reusable pattern."""
    assert _extract_rule_pattern(memo) == expected


# ---------------------------------------------------------------------------
# link() with auto rule creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_link_creates_rule_with_clean_pattern(db_session: AsyncSession) -> None:
    """Linking a bank tx auto-creates a rule with the cleaned memo pattern."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)
    cat = await _create_category(db_session, user.id, "Games")

    bank = _bank_tx(acc.id, -4200, label="CARTE 23/03/26 STEAMGAMES.COM 42 CB*6338")
    exp = _expense(acc.id, -4200, category_id=cat.id, label="Jeux")
    db_session.add_all([bank, exp])
    await db_session.flush()

    from budgie.schemas.reconciliation import LinkRequest

    result = await svc.link(
        db_session, user.id, LinkRequest(bank_tx_id=bank.id, expense_id=exp.id)
    )

    assert result.created_rule is not None
    assert result.created_rule.pattern == "STEAMGAMES.COM"
    assert result.created_rule.match_field == "memo"
    assert result.created_rule.match_type == "contains"
    assert result.created_rule.category_id == cat.id


@pytest.mark.asyncio
async def test_link_no_duplicate_rule(db_session: AsyncSession) -> None:
    """Linking a second time with the same pattern does not create a duplicate rule."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)
    cat = await _create_category(db_session, user.id, "Games")

    # Pre-existing rule for the same pattern
    existing = CategoryRule(
        user_id=user.id,
        pattern="STEAMGAMES.COM",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
    )
    db_session.add(existing)

    bank = _bank_tx(acc.id, -4200, label="CARTE 23/03/26 STEAMGAMES.COM 42 CB*6338")
    exp = _expense(acc.id, -4200, category_id=cat.id, label="Jeux")
    db_session.add_all([bank, exp])
    await db_session.flush()

    from budgie.schemas.reconciliation import LinkRequest

    result = await svc.link(
        db_session, user.id, LinkRequest(bank_tx_id=bank.id, expense_id=exp.id)
    )

    assert result.created_rule is None


@pytest.mark.asyncio
async def test_link_rule_exact_amount(db_session: AsyncSession) -> None:
    """rule_amount_mode='exact' sets min_amount == max_amount == abs(bank.amount)."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)
    cat = await _create_category(db_session, user.id, "Transport")

    bank = _bank_tx(acc.id, -2500, label="CARTE 01/01/26 RATP AGENCE")
    exp = _expense(acc.id, -2500, category_id=cat.id, label="Navigo")
    db_session.add_all([bank, exp])
    await db_session.flush()

    from budgie.schemas.reconciliation import LinkRequest

    result = await svc.link(
        db_session,
        user.id,
        LinkRequest(bank_tx_id=bank.id, expense_id=exp.id, rule_amount_mode="exact"),
    )

    assert result.created_rule is not None
    assert result.created_rule.min_amount == 2500
    assert result.created_rule.max_amount == 2500


@pytest.mark.asyncio
async def test_link_rule_percent_tolerance(db_session: AsyncSession) -> None:
    """rule_amount_mode='percent' sets min/max as ±pct% of abs(bank.amount)."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)
    cat = await _create_category(db_session, user.id, "Food")

    bank = _bank_tx(acc.id, -1000, label="CARTE 05/01/26 MONOPRIX")
    exp = _expense(acc.id, -1000, category_id=cat.id, label="Courses")
    db_session.add_all([bank, exp])
    await db_session.flush()

    from budgie.schemas.reconciliation import LinkRequest

    result = await svc.link(
        db_session,
        user.id,
        LinkRequest(
            bank_tx_id=bank.id,
            expense_id=exp.id,
            rule_amount_mode="percent",
            rule_amount_tolerance_pct=20,
        ),
    )

    assert result.created_rule is not None
    assert result.created_rule.min_amount == 800  # 1000 * 0.80
    assert result.created_rule.max_amount == 1200  # 1000 * 1.20


@pytest.mark.asyncio
async def test_link_rule_transaction_type(db_session: AsyncSession) -> None:
    """rule_transaction_type is stored on the auto-created rule."""
    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)
    cat = await _create_category(db_session, user.id, "Bills")

    bank = _bank_tx(acc.id, -5000, label="PRLV SEPA EDF CONTRAT 99")
    exp = _expense(acc.id, -5000, category_id=cat.id, label="EDF")
    db_session.add_all([bank, exp])
    await db_session.flush()

    from budgie.schemas.reconciliation import LinkRequest

    result = await svc.link(
        db_session,
        user.id,
        LinkRequest(
            bank_tx_id=bank.id,
            expense_id=exp.id,
            rule_transaction_type="debit",
        ),
    )

    assert result.created_rule is not None
    assert result.created_rule.transaction_type == "debit"


@pytest.mark.asyncio
async def test_link_skip_rule(db_session: AsyncSession) -> None:
    """skip_rule=True prevents any CategoryRule from being created."""
    from budgie.schemas.reconciliation import LinkRequest

    user = await _create_user(db_session)
    acc = await _create_account(db_session, user.id)
    cat = await _create_category(db_session, user.id, "Bills")

    bank = _bank_tx(acc.id, -3000, label="PRLV SEPA ORANGE SA CONTRAT 12345")
    exp = _expense(acc.id, -3000, category_id=cat.id, label="Orange mobile")
    db_session.add_all([bank, exp])
    await db_session.flush()

    result = await svc.link(
        db_session,
        user.id,
        LinkRequest(
            bank_tx_id=bank.id,
            expense_id=exp.id,
            skip_rule=True,
            rule_amount_mode="exact",
            rule_transaction_type="debit",
        ),
    )

    assert result.created_rule is None

    from sqlalchemy import select as sa_select

    rules = (
        (
            await db_session.execute(
                sa_select(CategoryRule).where(CategoryRule.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert rules == []


# ---------------------------------------------------------------------------
# _matches_rule — amount & transaction_type filters
# ---------------------------------------------------------------------------


def _make_rule(**kwargs: object) -> CategoryRule:
    """Build a CategoryRule with sensible defaults for unit tests."""
    defaults: dict[str, object] = {
        "user_id": 1,
        "pattern": "apple",
        "match_field": "memo",
        "match_type": "contains",
        "category_id": 1,
        "priority": 0,
        "transaction_type": "any",
        "min_amount": None,
        "max_amount": None,
    }
    defaults.update(kwargs)
    return CategoryRule(**defaults)


def _make_tx(amount: int, memo: str = "APPLE.COM/BILL") -> Transaction:
    """Build a minimal Transaction for unit tests."""
    tx = Transaction()
    tx.amount = amount
    tx.memo = memo
    return tx


def test_matches_rule_exact_amount_pass() -> None:
    """A transaction whose abs(amount) equals the exact bounds must match."""
    rule = _make_rule(min_amount=2595, max_amount=2595)
    assert _matches_rule(rule, _make_tx(-2595))


def test_matches_rule_exact_amount_fail_over() -> None:
    """A transaction 1 centime above the exact bound must not match."""
    rule = _make_rule(min_amount=2595, max_amount=2595)
    assert not _matches_rule(rule, _make_tx(-2596))


def test_matches_rule_exact_amount_fail_under() -> None:
    """A transaction 1 centime below the exact bound must not match."""
    rule = _make_rule(min_amount=2595, max_amount=2595)
    assert not _matches_rule(rule, _make_tx(-2594))


def test_matches_rule_percent_tolerance_within() -> None:
    """A transaction within +-20 % of 1000 (800-1200) must match."""
    rule = _make_rule(min_amount=800, max_amount=1200)
    assert _matches_rule(rule, _make_tx(-1000))
    assert _matches_rule(rule, _make_tx(-800))
    assert _matches_rule(rule, _make_tx(-1200))


def test_matches_rule_percent_tolerance_outside() -> None:
    """A transaction outside ±20 % must not match."""
    rule = _make_rule(min_amount=800, max_amount=1200)
    assert not _matches_rule(rule, _make_tx(-799))
    assert not _matches_rule(rule, _make_tx(-1201))


def test_matches_rule_no_amount_constraint() -> None:
    """With min_amount=None and max_amount=None every amount must match."""
    rule = _make_rule(min_amount=None, max_amount=None)
    assert _matches_rule(rule, _make_tx(-1))
    assert _matches_rule(rule, _make_tx(-999999))


def test_matches_rule_transaction_type_debit_pass() -> None:
    """A debit rule must match a negative amount."""
    rule = _make_rule(transaction_type="debit")
    assert _matches_rule(rule, _make_tx(-2595))


def test_matches_rule_transaction_type_debit_fail() -> None:
    """A debit rule must NOT match a positive (credit) amount."""
    rule = _make_rule(transaction_type="debit")
    assert not _matches_rule(rule, _make_tx(2595))


def test_matches_rule_transaction_type_credit_pass() -> None:
    """A credit rule must match a positive amount."""
    rule = _make_rule(transaction_type="credit")
    assert _matches_rule(rule, _make_tx(2595))


def test_matches_rule_transaction_type_credit_fail() -> None:
    """A credit rule must NOT match a negative (debit) amount."""
    rule = _make_rule(transaction_type="credit")
    assert not _matches_rule(rule, _make_tx(-2595))


def test_matches_rule_pattern_miss() -> None:
    """A transaction whose memo does not contain the pattern must not match."""
    rule = _make_rule(pattern="netflix")
    assert not _matches_rule(rule, _make_tx(-999, memo="APPLE.COM/BILL"))
