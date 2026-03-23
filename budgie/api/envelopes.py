"""Envelope management router."""

from fastapi import APIRouter, HTTPException, status

from budgie.api.deps import CurrentUser, DBSession
from budgie.schemas.envelope import (
    CategoryRef,
    EnvelopeCreate,
    EnvelopeRead,
    EnvelopeUpdate,
)
from budgie.services.envelope import (
    create_envelope,
    delete_envelope,
    get_envelope,
    get_envelopes,
    update_envelope,
)

router = APIRouter(prefix="/api/envelopes", tags=["envelopes"])


def _to_envelope_read(env: object) -> EnvelopeRead:
    """Convert an Envelope ORM instance to EnvelopeRead schema.

    Categories need group_name which requires joining through the ORM
    relationship (group loaded via selectin on Category.group).

    Args:
        env: Envelope ORM instance with categories loaded.

    Returns:
        EnvelopeRead pydantic schema.
    """
    from budgie.models.envelope import Envelope as EnvelopeModel

    assert isinstance(env, EnvelopeModel)
    cats = [
        CategoryRef(id=c.id, name=c.name, group_name=c.group.name)
        for c in env.categories
    ]
    return EnvelopeRead(
        id=env.id,
        name=env.name,
        envelope_type=env.envelope_type,
        period=env.period,
        target_amount=env.target_amount,
        stop_on_target=env.stop_on_target,
        rollover=env.rollover,
        sort_order=env.sort_order,
        emoji=env.emoji,
        categories=cats,
    )


@router.get("", response_model=list[EnvelopeRead])
async def list_envelopes(
    db: DBSession,
    current_user: CurrentUser,
) -> list[EnvelopeRead]:
    """List all envelopes for the current user, ordered by sort_order.

    Args:
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        List of envelope schemas.
    """
    envelopes = await get_envelopes(db, current_user.id)
    return [_to_envelope_read(e) for e in envelopes]


@router.post("", response_model=EnvelopeRead, status_code=status.HTTP_201_CREATED)
async def create_envelope_route(
    payload: EnvelopeCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> EnvelopeRead:
    """Create a new envelope for the current user.

    Args:
        payload: Envelope creation data.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        The created envelope.
    """
    envelope = await create_envelope(db, current_user.id, payload)
    return _to_envelope_read(envelope)


@router.put("/{envelope_id}", response_model=EnvelopeRead)
async def update_envelope_route(
    envelope_id: int,
    payload: EnvelopeUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> EnvelopeRead:
    """Update an existing envelope.

    Args:
        envelope_id: Envelope primary key.
        payload: Update data (partial).
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        The updated envelope.

    Raises:
        HTTPException: 404 if envelope not found or doesn't belong to user.
    """
    envelope = await get_envelope(db, envelope_id, current_user.id)
    if envelope is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Envelope not found"
        )
    updated = await update_envelope(db, envelope, payload)
    return _to_envelope_read(updated)


@router.delete("/{envelope_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_envelope_route(
    envelope_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Delete an envelope and its budget allocations.

    Args:
        envelope_id: Envelope primary key.
        db: Async database session.
        current_user: JWT-authenticated user.

    Raises:
        HTTPException: 404 if envelope not found or doesn't belong to user.
    """
    envelope = await get_envelope(db, envelope_id, current_user.id)
    if envelope is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Envelope not found"
        )
    await delete_envelope(db, envelope)
