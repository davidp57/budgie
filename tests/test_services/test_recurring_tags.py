"""Tests for the tags of recurring payments, with encrypted names."""

from __future__ import annotations

import os

from budgie.models.recurring_payment import RecurringTag, recurring_payment_tags
from budgie.models.user import User
from budgie.schemas.recurring import RecurringKind, RecurringPaymentCreate
from budgie.services import recurring as svc
from budgie.services import recurring_tags as tags
from budgie.services.data_migration import encrypt_user_data
from budgie.services.recurring_detection import Period
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

KEY = os.urandom(32)


async def _user(db: AsyncSession, name: str = "alice") -> int:
    user = User(username=name, hashed_password="x")
    db.add(user)
    await db.commit()
    return user.id


async def _payment(
    db: AsyncSession, user_id: int, key: str = "STREAMFLIX", kb: bytes | None = KEY
) -> int:
    return await svc.create_payment(
        db,
        RecurringPaymentCreate(
            key=key,
            name=key.title(),
            amount=1399,
            period=Period.MONTHLY,
            kind=RecurringKind.SUBSCRIPTION,
        ),
        user_id,
        session_key=kb,
    )


async def test_tag_names_are_encrypted_at_rest(db_session: AsyncSession) -> None:
    user_id = await _user(db_session)
    tag = await tags.create_tag(db_session, "Téléphone", user_id, session_key=KEY)

    stored = (await db_session.execute(select(RecurringTag))).scalar_one()
    assert "Téléphone" not in stored.name
    assert tag.name == "Téléphone"
    listed = await tags.list_tags(db_session, user_id, session_key=KEY)
    assert [t.name for t in listed] == ["Téléphone"]


async def test_creating_an_existing_name_returns_the_same_tag(
    db_session: AsyncSession,
) -> None:
    user_id = await _user(db_session)
    first = await tags.create_tag(db_session, "Épargne", user_id, session_key=KEY)
    again = await tags.create_tag(db_session, "  épargne ", user_id, session_key=KEY)

    assert again.id == first.id
    assert again.name == "Épargne"
    assert len((await db_session.execute(select(RecurringTag))).all()) == 1


async def test_tags_are_listed_by_name_and_per_user(db_session: AsyncSession) -> None:
    alice = await _user(db_session)
    bob = await _user(db_session, "bob")
    await tags.create_tag(db_session, "Streaming", alice, session_key=KEY)
    await tags.create_tag(db_session, "assurance", alice, session_key=KEY)
    await tags.create_tag(db_session, "Streaming", bob, session_key=None)

    listed = await tags.list_tags(db_session, alice, session_key=KEY)
    assert [t.name for t in listed] == ["assurance", "Streaming"]
    assert len(await tags.list_tags(db_session, bob, session_key=None)) == 1


async def test_tagging_checks_both_owners(db_session: AsyncSession) -> None:
    alice = await _user(db_session)
    bob = await _user(db_session, "bob")
    alice_payment = await _payment(db_session, alice)
    bob_payment = await _payment(db_session, bob, kb=None)
    alice_tag = await tags.create_tag(db_session, "Streaming", alice, session_key=KEY)
    bob_tag = await tags.create_tag(db_session, "Streaming", bob, session_key=None)

    assert await tags.tag_payment(db_session, alice_payment, alice_tag.id, alice)
    assert not await tags.tag_payment(db_session, alice_payment, bob_tag.id, alice)
    assert not await tags.tag_payment(db_session, bob_payment, alice_tag.id, alice)
    assert not await tags.untag_payment(db_session, alice_payment, alice_tag.id, bob)
    assert not await tags.delete_tag(db_session, alice_tag.id, bob)

    assert await tags.tags_by_payment(db_session, alice) == {
        alice_payment: [alice_tag.id]
    }
    assert await tags.tags_by_payment(db_session, bob) == {}


async def test_tagging_twice_keeps_one_link(db_session: AsyncSession) -> None:
    user_id = await _user(db_session)
    payment = await _payment(db_session, user_id)
    tag = await tags.create_tag(db_session, "Streaming", user_id, session_key=KEY)

    assert await tags.tag_payment(db_session, payment, tag.id, user_id)
    assert await tags.tag_payment(db_session, payment, tag.id, user_id)

    links = (await db_session.execute(select(recurring_payment_tags))).all()
    assert len(links) == 1


async def test_untagging_and_deleting(db_session: AsyncSession) -> None:
    user_id = await _user(db_session)
    first = await _payment(db_session, user_id)
    second = await _payment(db_session, user_id, "MUSIC")
    tag = await tags.create_tag(db_session, "Loisirs", user_id, session_key=KEY)
    await tags.tag_payment(db_session, first, tag.id, user_id)
    await tags.tag_payment(db_session, second, tag.id, user_id)

    assert await tags.untag_payment(db_session, first, tag.id, user_id)
    assert await tags.tags_by_payment(db_session, user_id) == {second: [tag.id]}

    assert await tags.delete_tag(db_session, tag.id, user_id)
    assert await tags.tags_by_payment(db_session, user_id) == {}
    assert await tags.list_tags(db_session, user_id, session_key=KEY) == []


async def test_forgetting_a_payment_drops_its_links(db_session: AsyncSession) -> None:
    user_id = await _user(db_session)
    payment = await _payment(db_session, user_id)
    tag = await tags.create_tag(db_session, "Streaming", user_id, session_key=KEY)
    await tags.tag_payment(db_session, payment, tag.id, user_id)

    assert await svc.delete_payment(db_session, payment, user_id)

    assert (await db_session.execute(select(recurring_payment_tags))).all() == []
    assert len(await tags.list_tags(db_session, user_id, session_key=KEY)) == 1


async def test_a_merge_keeps_the_tags_of_the_absorbed_payment(
    db_session: AsyncSession,
) -> None:
    user_id = await _user(db_session)
    target = await _payment(db_session, user_id)
    other = await _payment(db_session, user_id, "OLDSTREAM")
    shared = await tags.create_tag(db_session, "Streaming", user_id, session_key=KEY)
    own = await tags.create_tag(db_session, "Famille", user_id, session_key=KEY)
    await tags.tag_payment(db_session, target, shared.id, user_id)
    await tags.tag_payment(db_session, other, shared.id, user_id)
    await tags.tag_payment(db_session, other, own.id, user_id)

    assert await svc.merge_payments(db_session, target, other, user_id, session_key=KEY)

    assert await tags.tags_by_payment(db_session, user_id) == {
        target: sorted([shared.id, own.id])
    }


async def test_a_reset_forgets_the_tags(db_session: AsyncSession) -> None:
    user_id = await _user(db_session)
    payment = await _payment(db_session, user_id)
    tag = await tags.create_tag(db_session, "Streaming", user_id, session_key=KEY)
    await tags.tag_payment(db_session, payment, tag.id, user_id)

    await svc.reset_payments(db_session, user_id)

    assert await tags.list_tags(db_session, user_id, session_key=KEY) == []
    assert (await db_session.execute(select(recurring_payment_tags))).all() == []


async def test_setting_up_encryption_encrypts_tag_names(
    db_session: AsyncSession,
) -> None:
    user_id = await _user(db_session)
    await tags.create_tag(db_session, "Téléphone", user_id, session_key=None)

    await encrypt_user_data(db_session, user_id, KEY)

    stored = (await db_session.execute(select(RecurringTag))).scalar_one()
    assert "Téléphone" not in stored.name
    listed = await tags.list_tags(db_session, user_id, session_key=KEY)
    assert [t.name for t in listed] == ["Téléphone"]
