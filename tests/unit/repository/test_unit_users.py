import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from collections.abc import Sequence

from src.database.models import User
from src.repository.users import UserRepository
from src.schemas import UserCreate


@pytest.fixture
def mock_session():
    """Fixture to provide a mocked asynchronous database session."""
    mock_session = AsyncMock(spec=AsyncSession)
    return mock_session

@pytest.fixture
def user_repository(mock_session):
    """Fixture to provide an instance of UserRepository."""
    return UserRepository(mock_session)

@pytest.fixture
def user_data():
    """Fixture for standard user creation data."""
    return UserCreate(
        username="testuser", email="test@example.com", password="secret"
    )

@pytest.fixture
def existing_user():
    """Fixture for an existing User model instance."""
    return User(
        id=1, username="testuser", email="test@example.com", hashed_password="secret_hash", confirmed=False
    )


# --- SETUP HELPERS ---

def setup_mock_execute_single(mock_session, result_value: User | None):
    """Configures mock_session.execute to return a single scalar or None."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = result_value
    mock_session.execute = AsyncMock(return_value=mock_result)

def setup_mock_execute_all(mock_session, result_list: Sequence[User]):
    """Configures mock_session.execute to return a list of User objects."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = result_list
    mock_session.execute = AsyncMock(return_value=mock_result)


# ==============================================================================
# 1. READ/GET METHODS
# ==============================================================================

@pytest.mark.asyncio
async def test_get_all(user_repository, mock_session, existing_user):
    """Tests retrieval of all users."""
    setup_mock_execute_all(mock_session, [existing_user])
    
    users = await user_repository.get_all()
    
    assert len(users) == 1
    assert users[0].id == 1
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_by_id_success(user_repository, mock_session, existing_user):
    """Tests successful retrieval of a user by ID."""
    setup_mock_execute_single(mock_session, existing_user)
    
    user = await user_repository.get_user_by_id(user_id=1)
    
    assert user is not None
    assert user.id == 1


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(user_repository, mock_session):
    """Tests retrieval of a user by ID when not found (expect None)."""
    setup_mock_execute_single(mock_session, None)
    
    user = await user_repository.get_user_by_id(user_id=999)
    
    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(user_repository, mock_session):
    """Tests retrieval of a user by email when not found (expect None)."""
    setup_mock_execute_single(mock_session, None)
    
    user = await user_repository.get_user_by_email(email="nonexistent@example.com")
    
    assert user is None


# ==============================================================================
# 2. CREATE METHODS
# ==============================================================================

@pytest.mark.asyncio
async def test_create_user_success(user_repository, mock_session, user_data):
    """Tests successful creation of a new user."""
    # Ensure get_user_by_email is mocked to return None if needed, 
    # but the method doesn't call it, so we only test the commit/refresh logic.
    
    created_user = await user_repository.create_user(body=user_data, avatar="http://test.url")
    
    # Check attributes of the instantiated User object
    assert created_user.username == user_data.username
    assert created_user.avatar == "http://test.url"
    
    # Check DB operations
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(created_user)


# ==============================================================================
# 3. UPDATE/CONFIRM METHODS
# ==============================================================================

@pytest.mark.asyncio
async def test_confirmed_email_success(user_repository, mock_session, existing_user):
    """Tests successful confirmation of user email."""
    # Mock get_user_by_email to return the user
    setup_mock_execute_single(mock_session, existing_user)
    
    # Set initial state
    existing_user.confirmed = False
    
    await user_repository.confirmed_email(email=existing_user.email)
    
    # Check state change
    assert existing_user.confirmed is True
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirmed_email_user_not_found(user_repository, mock_session):
    """Tests confirmation when user is not found (expect AttributeError)."""
    setup_mock_execute_single(mock_session, None)
    
    # The code relies on get_user_by_email returning User, 
    # so accessing user.confirmed raises AttributeError if None is returned.
    with pytest.raises(AttributeError):
        await user_repository.confirmed_email(email="nonexistent@example.com")
    
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_avatar_url_success(user_repository, mock_session, existing_user):
    """Tests successful update of the user's avatar URL."""
    setup_mock_execute_single(mock_session, existing_user)
    new_url = "http://new.avatar.url"
    
    updated_user = await user_repository.update_avatar_url(email=existing_user.email, url=new_url)
    
    assert updated_user.avatar == new_url
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(existing_user)


@pytest.mark.asyncio
async def test_set_new_password_success(user_repository, mock_session, existing_user):
    """Tests successful update of the user's hashed password."""
    setup_mock_execute_single(mock_session, existing_user)
    new_hash = "new_secure_hash"
    
    updated_user = await user_repository.set_new_password(email=existing_user.email, new_password_hash=new_hash)
    
    assert updated_user.hashed_password == new_hash
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(existing_user)

@pytest.mark.asyncio
async def test_update_avatar_url_user_not_found(user_repository, mock_session):
    """Tests update when user is not found (expect AttributeError)."""
    setup_mock_execute_single(mock_session, None)
    
    with pytest.raises(AttributeError):
        await user_repository.update_avatar_url(email="nonexistent@example.com", url="http://fail.url")
    
    mock_session.commit.assert_not_awaited()

@pytest.mark.asyncio
async def test_set_new_password_user_not_found(user_repository, mock_session):
    """Tests password update when user is not found (expect AttributeError)."""
    setup_mock_execute_single(mock_session, None)
    
    with pytest.raises(AttributeError):
        await user_repository.set_new_password(email="nonexistent@example.com", new_password_hash="new_hash")
    
    mock_session.commit.assert_not_awaited()