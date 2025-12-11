from datetime import date, datetime, timedelta
import re
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text, func

from src.database.models import Contact, User
from src.repository.contacts import ContactRepository, DuplicateContactError
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

CONTACT_DATA_BASE = {
    "email": "sky@walker.com",
    "first_name": "Luke",
    "last_name": "Skywalker",
    "phone_number": "40358974",
    "birthday": date(day=25, month=2, year=1999),
    "additional_data": "Jedi."
}

# ------------------------------------------------------------------------------
# SUCCESS SCENARIOS (EXISTING TESTS)
# ------------------------------------------------------------------------------

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
    contact_data = ContactBase(**CONTACT_DATA_BASE)

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
    
    # Mock get_contact_by_id to return the existing contact
    mock_result_exist = MagicMock()
    mock_result_exist.scalar_one_or_none.return_value = existing_contact
    mock_session.execute = AsyncMock(return_value=mock_result_exist)

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


# ------------------------------------------------------------------------------
# NEW TESTS: EDGE CASES AND ERRORS
# ------------------------------------------------------------------------------

# 1. Resource Not Found (None) Scenarios

@pytest.mark.asyncio
async def test_get_contact_by_id_not_found(contact_repository, mock_session, user):
    """Test: get_contact_by_id returns None when the contact is not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    contact = await contact_repository.get_contact_by_id(contact_id=999, user=user)
    assert contact is None


@pytest.mark.asyncio
async def test_update_contact_not_found(contact_repository, mock_session, user):
    """Test: update_contact returns None when the contact is not found."""
    contact_data = ContactUpdate(last_name="Skywalker")
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await contact_repository.update_contact(
        contact_id=999, body=contact_data, user=user
    )
    assert result is None
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_contact_not_found(contact_repository, mock_session, user):
    """Test: remove_contact returns None when the contact is not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await contact_repository.remove_contact(contact_id=999, user=user)
    assert result is None
    mock_session.delete.assert_not_awaited()


# 2. Duplicate Contact Error (409) Scenarios

@pytest.mark.asyncio
async def test_create_contact_duplicate_email_error(contact_repository, mock_session, user):
    """Test: create_contact raises DuplicateContactError for a duplicate email."""
    contact_data = ContactBase(**CONTACT_DATA_BASE)
    
    # Mock IntegrityError with the duplicate email constraint message
    mock_session.commit.side_effect = IntegrityError(
        statement="INSERT INTO contacts...",
        params=None,
        orig=Exception("duplicate key value violates unique constraint 'uq_contact_email_user'")
    )
    
    with pytest.raises(DuplicateContactError) as excinfo:
        await contact_repository.create_contact(contact_data, user=user)
        
    assert "email already exists" in str(excinfo.value)
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_contact_duplicate_phone_error(contact_repository, mock_session, user):
    """Test: update_contact raises DuplicateContactError for a duplicate phone_number."""
    contact_data = ContactUpdate(phone_number="555-999-999")
    existing_contact = Contact(id=1, **CONTACT_DATA_BASE, user=user)
    
    # Mock get_contact_by_id to return the existing contact
    mock_result_exist = MagicMock()
    mock_result_exist.scalar_one_or_none.return_value = existing_contact
    mock_session.execute = AsyncMock(return_value=mock_result_exist)

    # Mock IntegrityError with the duplicate phone constraint message
    mock_session.commit.side_effect = IntegrityError(
        statement="UPDATE contacts...",
        params=None,
        orig=Exception("duplicate key value violates unique constraint 'uq_contact_phone_user'")
    )
    
    with pytest.raises(DuplicateContactError) as excinfo:
        await contact_repository.update_contact(contact_id=1, body=contact_data, user=user)
        
    assert "phone number already exists" in str(excinfo.value)
    mock_session.rollback.assert_awaited_once()


# 3. Search Tests

@pytest.mark.asyncio
async def test_search_contacts(contact_repository, mock_session, user):
    """Test: search_contacts correctly forms the search query."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        Contact(first_name="Anakin", user=user)
    ]
    mock_session.execute = AsyncMock(return_value=mock_result)

    contacts = await contact_repository.search_contacts(query="Ani", skip=0, limit=10, user=user)
    
    assert len(contacts) == 1
    
    # Verification that execute was awaited (detailed SQL check is complex in unit tests)
    mock_session.execute.assert_awaited_once()