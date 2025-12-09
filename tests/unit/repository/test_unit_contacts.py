from datetime import datetime

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.repository.contacts import ContactRepository
from src.schemas import ContactBase, ContactUpdate


@pytest.fixture
def mock_session():
    mock_session = AsyncMock(spec=AsyncSession)
    return mock_session


@pytest.fixture
def contact_repository(mock_session):
    return ContactRepository(mock_session)


@pytest.fixture
def user():
    return User(id=1, username="testuser")


@pytest.mark.asyncio
async def test_get_contacts(contact_repository, mock_session, user):
    # Setup mock
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        Contact(first_name="Luke", user=user)
    ]
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Call method
    contacts = await contact_repository.get_contacts(skip=0, limit=10, user=user)
    # Assertions
    assert len(contacts) == 1
    for contact in contacts:
        assert contact.user.id == 1
        assert contact.first_name == "Luke"


@pytest.mark.asyncio
async def test_get_contact_by_id(contact_repository, mock_session, user):
    # Setup mock
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = Contact(
        id=1, first_name="Luke", user=user
    )
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Call method
    contact = await contact_repository.get_contact_by_id(contact_id=1, user=user)
    # Assertions
    assert contact is not None
    assert contact.id == 1
    assert contact.first_name == "Luke"


@pytest.mark.asyncio
async def test_create_contact(contact_repository, mock_session, user):
    contact_data = ContactBase(
        email="sky@walker.com",
        first_name="Luke",
        last_name="Skywalker",
        phone_number="40358974",
        birthday=datetime(day=25, month=2, year=1999),
        additional_data="",
    )

    # Call method
    created_contact = await contact_repository.create_contact(contact_data, user=user)

    # Assertions
    assert created_contact is not None
    assert isinstance(created_contact, Contact)
    assert created_contact.first_name == "Luke"
    assert created_contact.email == "sky@walker.com"
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(created_contact)


@pytest.mark.asyncio
async def test_update_contact(contact_repository, mock_session, user):
    # Setup
    contact_data = ContactUpdate(last_name="Skywalker")
    existing_contact = Contact(id=1, first_name="Luke", last_name="Oldman", user=user)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_contact
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Call method
    result = await contact_repository.update_contact(
        contact_id=1, body=contact_data, user=user
    )

    # Assertions
    assert result is not None
    assert result.first_name == "Luke"
    assert result.last_name == "Skywalker"
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(existing_contact)


@pytest.mark.asyncio
async def test_remove_contact(contact_repository, mock_session, user):
    # Setup
    existing_contact = Contact(id=1, first_name="Luke", last_name="Oldman", user=user)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_contact
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Call method
    result = await contact_repository.remove_contact(contact_id=1, user=user)

    # Assertions
    assert result is not None
    assert result.last_name == "Oldman"
    mock_session.delete.assert_awaited_once_with(existing_contact)
    mock_session.commit.assert_awaited_once()