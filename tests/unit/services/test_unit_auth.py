import pickle

import pytest
from jose import jwt
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import HTTPException, status

from src.services.auth import (
    create_access_token,
    get_current_user,
    get_email_from_token,
    create_email_token,
    get_admin_user,
)
from src.database.models import User, UserRole
from src.conf.config import config


@pytest.mark.asyncio
async def test_create_access_token():
    data = {"sub": "test@example.com"}
    token = await create_access_token(data, expires_delta=60)
    decoded = jwt.decode(
        token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
    )
    assert decoded["sub"] == "test@example.com"
    assert "exp" in decoded


@pytest.mark.asyncio
@patch("src.services.auth.redis.from_url")
@patch("src.services.auth.UserService")
async def test_get_current_user_from_redis(mock_user_service_cls, mock_redis):
    """Test: User is successfully retrieved from the Redis cache."""
    mock_user = User(id=1, username="testuser", role=UserRole.USER)
    token = jwt.encode(
        {"sub": "testuser"}, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM
    )

    mock_r = MagicMock()
    mock_r.get.return_value = pickle.dumps(mock_user)
    mock_redis.return_value = mock_r

    mock_user_service = AsyncMock()
    mock_user_service_cls.return_value = mock_user_service

    result = await get_current_user(token=token, db=AsyncMock())
    assert result.username == "testuser"
    mock_r.get.assert_called_once_with("testuser")


@pytest.mark.asyncio
@patch("src.services.auth.redis.from_url")
@patch("src.services.auth.UserService")
async def test_get_current_user_from_db(mock_user_service_cls, mock_redis):
    """Test: User not found in cache, but successfully retrieved from DB and cached."""
    mock_user = User(id=1, username="testuser", role=UserRole.USER)
    token = jwt.encode(
        {"sub": "testuser"}, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM
    )

    mock_r = MagicMock()
    mock_r.get.return_value = None
    mock_redis.return_value = mock_r

    mock_user_service = AsyncMock()
    mock_user_service.get_user_by_username.return_value = mock_user
    mock_user_service_cls.return_value = mock_user_service

    result = await get_current_user(token=token, db=AsyncMock())
    assert result.username == "testuser"
    mock_user_service.get_user_by_username.assert_awaited_once_with("testuser")
    mock_r.set.assert_called_once()
    mock_r.expire.assert_called_once()


@pytest.mark.asyncio
@patch("src.services.auth.redis.from_url")
@patch("src.services.auth.UserService")
async def test_get_current_user_not_in_db(mock_user_service_cls, mock_redis):
    """Test: Token is valid, but user is not found in the DB (expect 401)."""
    token = jwt.encode(
        {"sub": "nonexistent_user"}, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM
    )

    mock_r = MagicMock()
    mock_r.get.return_value = None
    mock_redis.return_value = mock_r

    mock_user_service = AsyncMock()
    # Mock that user is not found
    mock_user_service.get_user_by_username.return_value = None
    mock_user_service_cls.return_value = mock_user_service

    with pytest.raises(HTTPException) as exc:
        await get_current_user(token=token, db=AsyncMock())
        
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in exc.value.detail


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """Test: Token has an incorrect format (expect 401)."""
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token="invalid.token.here", db=AsyncMock())
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_get_current_admin_user_success():
    """Test: User has ADMIN role (success)."""
    user = User(id=1, username="admin", role=UserRole.ADMIN)
    result = await get_admin_user(user)
    assert result == user

@pytest.mark.asyncio
async def test_get_current_admin_user_forbidden():
    """Test: User has USER role (forbidden, expect 403)."""
    user = User(id=1, username="user", role=UserRole.USER)
    with pytest.raises(HTTPException) as exc:
        await get_admin_user(user)
    assert exc.value.status_code == 403
    assert "Allowed only for Admin" in exc.value.detail


@pytest.mark.asyncio
async def test_get_email_from_token_valid():
    """Test: Successful retrieval of email from a valid token."""
    token = jwt.encode(
        {"sub": "test@example.com"},
        config.JWT_SECRET,
        algorithm=config.JWT_ALGORITHM,
    )
    email = await get_email_from_token(token)
    assert email == "test@example.com"


@pytest.mark.asyncio
async def test_get_email_from_token_invalid():
    """Test: Retrieval of email from an invalid token (expect 422)."""
    with pytest.raises(HTTPException) as exc:
        await get_email_from_token("invalid.token")
    assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "Invalid email verification token" in exc.value.detail


def test_create_email_token():
    """Test: Correct generation of email token with exp and iat."""
    token = create_email_token({"sub": "test@example.com"})
    decoded = jwt.decode(
        token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
    )
    assert decoded["sub"] == "test@example.com"
    assert "exp" in decoded
    assert "iat" in decoded