"""Recurring payments router: candidates, verdicts and subscription costs."""

from fastapi import APIRouter, HTTPException, Response, status

from budgie.api.deps import CurrentUser, DBSession, SessionKey
from budgie.schemas.recurring import (
    RecurringAliasCreate,
    RecurringCandidateRead,
    RecurringMerge,
    RecurringOverview,
    RecurringPaymentCreate,
    RecurringPaymentUpdate,
)
from budgie.services.ownership import ForeignReferenceError
from budgie.services.recurring import (
    accept_price,
    add_alias,
    create_payment,
    delete_payment,
    get_candidates,
    get_overview,
    merge_payments,
    remove_alias,
    update_payment,
)

router = APIRouter(prefix="/api/recurring", tags=["recurring"])

_NOT_FOUND = "Recurring payment not found"


@router.get("/candidates", response_model=list[RecurringCandidateRead])
async def list_candidates(
    db: DBSession,
    current_user: CurrentUser,
    session_key: SessionKey,
) -> list[RecurringCandidateRead]:
    """List the recurring debits the user has not classified yet.

    Args:
        db: Async database session.
        current_user: JWT-authenticated user.
        session_key: AES-256-GCM session key for decryption.

    Returns:
        Candidates, most expensive per month first.
    """
    return await get_candidates(db, current_user.id, session_key=session_key)


@router.get("", response_model=RecurringOverview)
async def overview(
    db: DBSession,
    current_user: CurrentUser,
    session_key: SessionKey,
) -> RecurringOverview:
    """Return the classified payments and the cost of the subscriptions.

    Args:
        db: Async database session.
        current_user: JWT-authenticated user.
        session_key: AES-256-GCM session key for decryption.

    Returns:
        The overview.
    """
    return await get_overview(db, current_user.id, session_key=session_key)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RecurringOverview)
async def classify(
    schema: RecurringPaymentCreate,
    db: DBSession,
    current_user: CurrentUser,
    session_key: SessionKey,
) -> RecurringOverview:
    """Record the user's verdict on a candidate.

    Args:
        schema: The verdict.
        db: Async database session.
        current_user: JWT-authenticated user.
        session_key: AES-256-GCM session key for encryption.

    Returns:
        The updated overview.
    """
    await create_payment(db, schema, current_user.id, session_key=session_key)
    return await get_overview(db, current_user.id, session_key=session_key)


@router.patch("/{payment_id}", response_model=RecurringOverview)
async def update(
    payment_id: int,
    schema: RecurringPaymentUpdate,
    db: DBSession,
    current_user: CurrentUser,
    session_key: SessionKey,
) -> RecurringOverview:
    """Rename, reclassify, categorize or cancel a payment.

    Args:
        payment_id: Payment primary key.
        schema: Fields to change.
        db: Async database session.
        current_user: JWT-authenticated user.
        session_key: AES-256-GCM session key for encryption.

    Returns:
        The updated overview.

    Raises:
        HTTPException: 404 if the payment or the category is not the user's.
    """
    try:
        found = await update_payment(
            db, payment_id, schema, current_user.id, session_key=session_key
        )
    except ForeignReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return await get_overview(db, current_user.id, session_key=session_key)


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def forget(
    payment_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> Response:
    """Forget a classification: its debits become a candidate again.

    Args:
        payment_id: Payment primary key.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        An empty 204 response.

    Raises:
        HTTPException: 404 if the payment is not the user's.
    """
    if not await delete_payment(db, payment_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{payment_id}/aliases", response_model=RecurringOverview)
async def merge_candidate(
    payment_id: int,
    schema: RecurringAliasCreate,
    db: DBSession,
    current_user: CurrentUser,
    session_key: SessionKey,
) -> RecurringOverview:
    """Merge a candidate's label into a classified payment ("same as…").

    Args:
        payment_id: Payment the label is merged into.
        schema: Label and amount of the candidate.
        db: Async database session.
        current_user: JWT-authenticated user.
        session_key: AES-256-GCM session key for encryption.

    Returns:
        The updated overview.

    Raises:
        HTTPException: 404 if the payment is not the user's.
    """
    if not await add_alias(
        db, payment_id, schema, current_user.id, session_key=session_key
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return await get_overview(db, current_user.id, session_key=session_key)


@router.post("/{payment_id}/merge", response_model=RecurringOverview)
async def merge(
    payment_id: int,
    schema: RecurringMerge,
    db: DBSession,
    current_user: CurrentUser,
    session_key: SessionKey,
) -> RecurringOverview:
    """Merge another classified payment into this one, which absorbs its labels.

    Args:
        payment_id: Payment that absorbs the other.
        schema: The payment to absorb.
        db: Async database session.
        current_user: JWT-authenticated user.
        session_key: AES-256-GCM session key for encryption.

    Returns:
        The updated overview.

    Raises:
        HTTPException: 404 if either payment is not the user's, or both are
            the same payment.
    """
    if not await merge_payments(
        db, payment_id, schema.other_id, current_user.id, session_key=session_key
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return await get_overview(db, current_user.id, session_key=session_key)


@router.delete("/{payment_id}/aliases/{alias_id}", response_model=RecurringOverview)
async def detach(
    payment_id: int,
    alias_id: int,
    db: DBSession,
    current_user: CurrentUser,
    session_key: SessionKey,
) -> RecurringOverview:
    """Detach a merged label: its debits become a candidate again.

    Args:
        payment_id: Payment the label is merged into.
        alias_id: Merged label to detach.
        db: Async database session.
        current_user: JWT-authenticated user.
        session_key: AES-256-GCM session key for decryption.

    Returns:
        The updated overview.

    Raises:
        HTTPException: 404 if the label is not one of the user's payment.
    """
    if not await remove_alias(db, payment_id, alias_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return await get_overview(db, current_user.id, session_key=session_key)


@router.post("/{payment_id}/accept-price", response_model=RecurringOverview)
async def accept_new_price(
    payment_id: int,
    db: DBSession,
    current_user: CurrentUser,
    session_key: SessionKey,
) -> RecurringOverview:
    """Take the latest debited amount as the new reference price.

    Args:
        payment_id: Payment primary key.
        db: Async database session.
        current_user: JWT-authenticated user.
        session_key: AES-256-GCM session key for decryption.

    Returns:
        The updated overview.

    Raises:
        HTTPException: 404 if the payment is not the user's.
    """
    if not await accept_price(db, payment_id, current_user.id, session_key=session_key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return await get_overview(db, current_user.id, session_key=session_key)
