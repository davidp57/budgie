"""Reconciliation (pointage) service.

Implements the logic for matching bank-imported transactions against
budget transactions (planned or real), and for finalising a reconciliation
session (clôture).

Terminology
-----------
* **bank_tx** — a Transaction with ``import_hash`` set (imported from bank).
* **expense**  — a Transaction with ``import_hash=None`` (budget entry).
* **link**     — ``expense.reconciled_with_id == bank_tx.id``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.account import Account
from budgie.models.category import Category
from budgie.models.category_rule import CategoryRule
from budgie.models.transaction import Transaction
from budgie.schemas.category_rule import CategoryRuleRead
from budgie.schemas.reconciliation import (
    BankTxRead,
    BudgetExpenseRead,
    ClotureRequest,
    ClotureResponse,
    LinkRead,
    LinkRequest,
    ReconciliationViewResponse,
    SuggestionRead,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Strips common French bank prefixes at the start of memo strings.
# e.g. "CARTE ", "VIR SEPA ", "PRLV SEPA ", "RETRAIT DAB ", etc.
_RE_MEMO_PREFIX = re.compile(
    r"^("
    r"CARTE\s+"
    r"|VIR(?:EMENT)?\s+(?:SEPA\s+)?"
    r"|PRLV(?:MT)?\s+(?:SEPA\s+)?"
    r"|PRELEVEMENT\s+(?:SEPA\s+)?"
    r"|CHEQUE\s+"
    r"|RETRAIT\s+(?:DAB\s+)?"
    r"|DEPOT\s+"
    r"|FACTURE\s+"
    r"|FRAIS\s+"
    r"|CPT\s+"
    r"|ACHAT\s+(?:CB\s+)?(?:INTERNET\s+)?"
    r")+",
    re.IGNORECASE,
)

# Removes date-like tokens anywhere in the string.
# Matches: DD/MM/YY, DD/MM/YYYY, DD-MM-YY, DD-MM-YYYY, and compact 6-8 digit forms.
_RE_DATE = re.compile(r"\b\d{2}[/\-\.]\d{2}[/\-\.]\d{2,4}\b|\b\d{6,8}\b")

# Removes card/terminal reference fragments: CB*XXXX, CB XXXX, XX*XXXX, N°…, REF…
_RE_CARD_REF = re.compile(r"\b[A-Z]{1,4}\*\S+|\bN°\S*|\bREF\s*\d+", re.IGNORECASE)

# Removes isolated numeric tokens (amounts, sequence numbers, etc.).
_RE_LONE_NUMBER = re.compile(r"(?<![.\w])\d+(?![.\w])")


def _extract_rule_pattern(memo: str) -> str | None:
    """Extract a clean, reusable pattern from a raw bank memo string.

    Applies the following transformations in order:
    1. Strip known bank-operation prefixes (CARTE, VIR, PRLV, …).
    2. Remove date-like tokens (DD/MM/YY, DDMMYYYY, …).
    3. Remove card/reference fragments (CB*XXXX, N°…, REF…).
    4. Remove isolated numbers (amounts, sequence numbers, …).
    5. Collapse whitespace and trim.

    Returns the cleaned string, or ``None`` when nothing meaningful remains
    (fewer than 3 characters after cleaning).

    Examples::

        "CARTE 23/03/26 STEAMGAMES.COM 42 CB*6338"  → "STEAMGAMES.COM"
        "VIR SEPA LOYER APPARTEMENT"                 → "LOYER APPARTEMENT"
        "PRLV SEPA EDF CONTRAT 12345678"             → "EDF CONTRAT"
        "RETRAIT DAB 23/03/26 75001 PARIS"           → "PARIS"

    Args:
        memo: Raw bank transaction memo/label.

    Returns:
        Cleaned pattern string, or ``None`` if the result is too short.
    """
    text = memo.strip()
    text = _RE_MEMO_PREFIX.sub("", text).strip()
    text = _RE_DATE.sub(" ", text).strip()
    text = _RE_CARD_REF.sub(" ", text).strip()
    text = _RE_LONE_NUMBER.sub(" ", text).strip()
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text if len(text) >= 3 else None


def _is_bank(tx: Transaction) -> bool:
    """Return True when *tx* was imported from a bank (has import_hash)."""
    return tx.import_hash is not None


def _matches_rule(rule: CategoryRule, tx: Transaction) -> bool:
    """Test whether *tx* matches *rule* using the rule's match logic."""
    # Bank imports store the merchant name in memo; we match against it
    # regardless of whether the rule targets the payee or memo field.
    value = tx.memo or ""
    if not value:
        return False
    if rule.match_type == "contains":
        return rule.pattern.lower() in value.lower()
    if rule.match_type == "exact":
        return rule.pattern.lower() == value.lower()
    if rule.match_type == "regex":
        return re.search(rule.pattern, value, re.IGNORECASE) is not None
    return False


def _score(bank: Transaction, exp: Transaction) -> float:
    """Compute a matching score between *bank* and *exp* (higher is better).

    Scoring combines:
    - Amount proximity (dominant): 1 / (1 + abs_diff_euros)
    - Date proximity (tiebreaker): 1 / (1 + days_diff)
    """
    amt_diff = abs(abs(bank.amount) - abs(exp.amount)) / 100.0  # euros
    date_diff = abs((bank.date - exp.date).days)
    return 1.0 / (1.0 + amt_diff) + 0.01 / (1.0 + date_diff)


async def _get_account(
    db: AsyncSession, account_id: int, user_id: int
) -> Account | None:
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _get_tx(db: AsyncSession, tx_id: int, user_id: int) -> Transaction | None:
    result = await db.execute(
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(Transaction.id == tx_id, Account.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _month_txs(
    db: AsyncSession, account_id: int, month: str
) -> Sequence[Transaction]:
    """Return all transactions for *account_id* in *month* (YYYY-MM)."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.account_id == account_id,
            func.strftime("%Y-%m", Transaction.date) == month,
        )
    )
    return result.scalars().all()


def _to_bank_read(tx: Transaction) -> BankTxRead:
    return BankTxRead(
        id=tx.id,
        date=tx.date,
        label=tx.memo or "",
        amount=tx.amount,
        import_hash=tx.import_hash,
    )


def _to_expense_read(tx: Transaction, cat_name: str | None = None) -> BudgetExpenseRead:
    return BudgetExpenseRead(
        id=tx.id,
        date=tx.date,
        label=tx.memo or "",
        amount=tx.amount,
        category_id=tx.category_id,
        category_name=cat_name,
        memo=None,
        status=tx.status,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_view(
    db: AsyncSession,
    user_id: int,
    account_id: int,
    month: str,
) -> ReconciliationViewResponse:
    """Return the full reconciliation view for *account_id* and *month*.

    Args:
        db: Async database session.
        user_id: Authenticated user.
        account_id: Account to reconcile.
        month: Month in YYYY-MM format.

    Returns:
        A :class:`ReconciliationViewResponse` with bank txs, budget expenses,
        confirmed links and rule-based suggestions.
    """
    account = await _get_account(db, account_id, user_id)
    if account is None:
        raise ValueError(f"Account {account_id} not found")

    all_txs = await _month_txs(db, account_id, month)
    bank_list = [tx for tx in all_txs if _is_bank(tx)]
    expense_list = [tx for tx in all_txs if not _is_bank(tx)]

    # Collect category names in one query
    cat_ids = {tx.category_id for tx in expense_list if tx.category_id is not None}
    cat_names: dict[int, str] = {}
    if cat_ids:
        cat_result = await db.execute(select(Category).where(Category.id.in_(cat_ids)))
        cat_names = {c.id: c.name for c in cat_result.scalars().all()}

    # Build confirmed links: expense.reconciled_with_id → bank tx
    linked_expense_ids = {
        tx.id for tx in expense_list if tx.reconciled_with_id is not None
    }
    linked_bank_ids = {
        tx.reconciled_with_id
        for tx in expense_list
        if tx.reconciled_with_id is not None
    }
    links = [
        LinkRead(bank_tx_id=tx.reconciled_with_id, expense_id=tx.id)
        for tx in expense_list
        if tx.reconciled_with_id is not None
    ]

    # Suggestions for unlinked transactions
    suggestions = await _build_suggestions(
        db,
        user_id,
        [b for b in bank_list if b.id not in linked_bank_ids],
        [e for e in expense_list if e.id not in linked_expense_ids],
        cat_names,
    )

    return ReconciliationViewResponse(
        account_id=account_id,
        month=month,
        bank_txs=[_to_bank_read(b) for b in bank_list],
        expenses=[
            _to_expense_read(e, cat_names.get(e.category_id))  # type: ignore[arg-type]
            for e in expense_list
        ],
        links=links,
        suggestions=suggestions,
    )


async def _build_suggestions(
    db: AsyncSession,
    user_id: int,
    unlinked_banks: list[Transaction],
    unlinked_expenses: list[Transaction],
    cat_names: dict[int, str],
) -> list[SuggestionRead]:
    """Build rule-based pairing suggestions.

    For each unlinked bank tx that matches a CategoryRule, find the
    best-scoring unlinked expense in the same category with the same sign.

    Each expense is only suggested once (greedy assignment by score).
    """
    if not unlinked_banks or not unlinked_expenses:
        return []

    # Load all rules for this user, ordered by priority desc
    rules_result = await db.execute(
        select(CategoryRule)
        .where(CategoryRule.user_id == user_id)
        .order_by(CategoryRule.priority.desc())
    )
    rules = list(rules_result.scalars().all())

    # Map bank_tx → matched category_id via rules
    bank_to_cat: dict[int, int] = {}
    for bank in unlinked_banks:
        for rule in rules:
            if _matches_rule(rule, bank):
                bank_to_cat[bank.id] = rule.category_id
                break

    if not bank_to_cat:
        return []

    # Build (bank, expense, score) candidates
    used_expense_ids: set[int] = set()
    suggestions: list[SuggestionRead] = []

    # Sort bank txs by best potential score (greedy, highest-score first)
    for bank in unlinked_banks:
        cat_id = bank_to_cat.get(bank.id)
        if cat_id is None:
            continue
        sign = -1 if bank.amount < 0 else 1
        candidates = [
            e
            for e in unlinked_expenses
            if e.id not in used_expense_ids
            and e.category_id == cat_id
            and ((-1 if e.amount < 0 else 1) == sign)
        ]
        if not candidates:
            continue
        best = max(candidates, key=lambda e: _score(bank, e))
        suggestions.append(
            SuggestionRead(
                bank_tx=_to_bank_read(bank),
                expense=_to_expense_read(best, cat_names.get(cat_id)),
                score=_score(bank, best),
            )
        )
        used_expense_ids.add(best.id)

    return suggestions


async def get_suggestions(
    db: AsyncSession,
    user_id: int,
    account_id: int,
    month: str,
) -> list[SuggestionRead]:
    """Return rule-based suggestions for unlinked transactions.

    Args:
        db: Async database session.
        user_id: Authenticated user.
        account_id: Account to analyse.
        month: Month in YYYY-MM format.

    Returns:
        List of :class:`SuggestionRead` with scoring.
    """
    view = await get_view(db, user_id, account_id, month)
    return view.suggestions


async def link(
    db: AsyncSession,
    user_id: int,
    req: LinkRequest,
) -> LinkRead:
    """Create a reconciliation link between a bank tx and a budget expense.

    Optionally adjusts the expense amount and stores a memo.

    Args:
        db: Async database session.
        user_id: Authenticated user.
        req: Link request payload.

    Returns:
        The newly created :class:`LinkRead`.

    Raises:
        ValueError: If either transaction is not found or the bank tx is
            already linked.
    """
    bank = await _get_tx(db, req.bank_tx_id, user_id)
    if bank is None:
        raise ValueError(f"Bank transaction {req.bank_tx_id} not found")
    if bank.import_hash is None:
        raise ValueError(
            f"Transaction {req.bank_tx_id} is not a bank-imported transaction"
        )

    expense = await _get_tx(db, req.expense_id, user_id)
    if expense is None:
        raise ValueError(f"Expense {req.expense_id} not found")
    if expense.import_hash is not None:
        raise ValueError(f"Transaction {req.expense_id} is not a budget expense")

    # Check the bank tx is not already linked via another expense (scoped to user)
    existing_result = await db.execute(
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Transaction.reconciled_with_id == req.bank_tx_id,
            Account.user_id == user_id,
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise ValueError(
            f"Bank transaction {req.bank_tx_id} is already linked to an expense"
        )

    if req.adjust_amount and bank.amount != expense.amount:
        expense.amount = bank.amount

    if req.memo is not None:
        expense.memo = req.memo

    expense.reconciled_with_id = bank.id

    # Auto-create a categorization rule on first link, if the bank tx has a
    # meaningful label and the expense belongs to a known category.
    new_rule: CategoryRule | None = None
    pattern = _extract_rule_pattern(bank.memo) if bank.memo else None
    if pattern and expense.category_id is not None:
        existing_result = await db.execute(
            select(CategoryRule).where(
                CategoryRule.user_id == user_id,
                CategoryRule.pattern == pattern,
                CategoryRule.match_field == "memo",
                CategoryRule.match_type == "contains",
                CategoryRule.category_id == expense.category_id,
            )
        )
        if existing_result.scalar_one_or_none() is None:
            new_rule = CategoryRule(
                user_id=user_id,
                pattern=pattern,
                match_field="memo",
                match_type="contains",
                category_id=expense.category_id,
                priority=0,
            )
            db.add(new_rule)

    await db.commit()

    if new_rule is not None:
        await db.refresh(new_rule)

    return LinkRead(
        bank_tx_id=bank.id,
        expense_id=expense.id,
        created_rule=CategoryRuleRead.model_validate(new_rule) if new_rule else None,
    )


async def unlink(
    db: AsyncSession,
    user_id: int,
    bank_tx_id: int,
) -> None:
    """Remove the reconciliation link for *bank_tx_id*.

    Args:
        db: Async database session.
        user_id: Authenticated user.
        bank_tx_id: ID of the bank transaction whose link should be removed.
    """
    result = await db.execute(
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Transaction.reconciled_with_id == bank_tx_id,
            Account.user_id == user_id,
        )
    )
    expense = result.scalar_one_or_none()
    if expense is not None:
        expense.reconciled_with_id = None
        await db.commit()


async def cloture(
    db: AsyncSession,
    user_id: int,
    req: ClotureRequest,
) -> ClotureResponse:
    """Finalise a reconciliation session.

    Marks all linked bank txs and their paired expenses as ``reconciled``.

    Args:
        db: Async database session.
        user_id: Authenticated user.
        req: Clôture request with account_id and month.

    Returns:
        A :class:`ClotureResponse` with reconciliation statistics.
    """
    account = await _get_account(db, req.account_id, user_id)
    if account is None:
        raise ValueError(f"Account {req.account_id} not found")

    all_txs = await _month_txs(db, req.account_id, req.month)
    bank_list = [tx for tx in all_txs if _is_bank(tx)]
    expense_list = [tx for tx in all_txs if not _is_bank(tx)]

    linked_bank_ids = {
        tx.reconciled_with_id
        for tx in expense_list
        if tx.reconciled_with_id is not None
    }

    reconciled_count = 0
    for tx in bank_list:
        if tx.id in linked_bank_ids:
            tx.status = "reconciled"
            reconciled_count += 1

    for tx in expense_list:
        if tx.reconciled_with_id is not None:
            tx.status = "reconciled"

    await db.commit()

    return ClotureResponse(
        linked_count=len(linked_bank_ids),
        total_bank_txs=len(bank_list),
        total_expenses=len(expense_list),
        reconciled_count=reconciled_count,
    )
