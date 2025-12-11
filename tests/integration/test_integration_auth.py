import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, UTC
from jose import jwt, JWTError

# Assuming imports from conftest are accessible
from tests.conftest import test_user
from src.conf.config import config
from src.database.models import User 

# === FIXTURES ===

@pytest.fixture(scope="module")
def new_user_data():
    """Data for a new, non-existent user in the test DB."""
    return {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "newpassword123",
    }

@pytest.fixture
def mock_redis_only():
    """Mocks Redis to return None, forcing get_current_user to check the DB."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    
    with patch("redis.from_url", return_value=mock_redis):
        yield mock_redis

@pytest.fixture
def valid_email_token():
    """Creates a valid JWT for email confirmation/password reset (valid for 20 minutes)."""
    expire = datetime.now(UTC) + timedelta(minutes=20)
    to_encode = {"sub": test_user["email"], "exp": expire}
    
    token = jwt.encode(
        to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM
    )
    return token

@pytest.fixture
def expired_email_token():
    """Creates an expired JWT for email confirmation/password reset."""
    expire = datetime.now(UTC) - timedelta(minutes=1)
    to_encode = {"sub": test_user["email"], "exp": expire}
    
    token = jwt.encode(
        to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM
    )
    return token

# === TESTS ===

# 1. Registration and Login Tests

@pytest.mark.asyncio
@patch("src.api.auth.send_verification_email")
async def test_register_user_success(
    mock_send_verify: MagicMock,
    client: TestClient, 
    new_user_data: dict, 
    mock_redis_only
):
    """
    Tests successful registration of a new user.
    """
    response = client.post(
        "/api/auth/register",
        json=new_user_data,
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    
    # Check that the background task was called
    mock_send_verify.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_duplicate_email(client: TestClient, mock_redis_only):
    """
    Tests registration with an already existing email (expecting 409 Conflict).
    """
    duplicate_data = {
        "username": "anotheruser",
        "email": test_user["email"],
        "password": "somepassword",
    }
    
    response = client.post(
        "/api/auth/register",
        json=duplicate_data,
    )
    
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "User with this email already exists."


@pytest.mark.asyncio
async def test_register_user_duplicate_username(client: TestClient, mock_redis_only):
    """
    Tests registration with an already existing username (expecting 409 Conflict).
    """
    duplicate_data = {
        "username": test_user["username"],
        "email": "newuniqueemail@example.com",
        "password": "somepassword",
    }
    
    response = client.post(
        "/api/auth/register",
        json=duplicate_data,
    )
    
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "User with that name already exists."


@pytest.mark.asyncio
async def test_login_user_success(client: TestClient, mock_redis_only):
    """
    Tests successful login of a confirmed user.
    """
    response = client.post(
        "/api/auth/login",
        data={"username": test_user["username"], "password": test_user["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_login_user_incorrect_password(client: TestClient, mock_redis_only):
    """
    Tests login with an incorrect password (expecting 401 Unauthorized).
    """
    response = client.post(
        "/api/auth/login",
        data={"username": test_user["username"], "password": "wrongpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Incorrect login or password"


@pytest.mark.asyncio
async def test_login_user_unconfirmed(client: TestClient, new_user_data: dict, mock_redis_only, caplog):
    """
    Tests login of a user whose email is not confirmed (expecting 401 Unauthorized).
    """
    unconfirmed_data = {
        "username": "unconfirmed_login",
        "email": "unconfirmed_login@example.com",
        "password": "testpass",
    }

    # Create unconfirmed user
    with patch("src.api.auth.send_verification_email"):
        client.post("/api/auth/register", json=unconfirmed_data)

    response = client.post(
        "/api/auth/login",
        data={"username": unconfirmed_data["username"], "password": unconfirmed_data["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Email address not confirmed"


# 2. Email Confirmation and Request Tests

@pytest.mark.asyncio
async def test_confirmed_email_success(client: TestClient, valid_email_token: str, mock_redis_only):
    """
    Tests successful email confirmation (expecting 200).
    """
    response = client.get(f"/api/auth/confirmed_email/{valid_email_token}")
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_confirmed_email_invalid_token(client: TestClient, mock_redis_only):
    """
    Tests email confirmation with an invalid token format (expecting 422 Unprocessable Content).
    """
    response = client.get("/api/auth/confirmed_email/totally_invalid_token_format")
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_confirmed_email_expired_token(client: TestClient, expired_email_token: str, mock_redis_only):
    """
    Tests email confirmation with an expired token (expecting 422 Unprocessable Content).
    """
    response = client.get(f"/api/auth/confirmed_email/{expired_email_token}")
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@patch("src.api.auth.send_verification_email")
async def test_request_email_success(
    mock_send_verify: MagicMock,
    client: TestClient, 
    new_user_data: dict,
    mock_redis_only
):
    """
    Tests the request for a new email confirmation link for an unconfirmed user.
    """
    # 1. Register a new user to guarantee existence in DB
    unconfirmed_data = {
        "username": "unconfirmed_req",
        "email": "unconfirmed_req@example.com",
        "password": "testpass",
    }
    with patch("src.api.auth.send_verification_email"):
        client.post("/api/auth/register", json=unconfirmed_data)
    
    mock_send_verify.reset_mock() 

    # 2. Execute the request_email
    response = client.post(
        "/api/auth/request_email",
        json={"email": unconfirmed_data["email"]},
    )

    assert response.status_code == status.HTTP_200_OK
    mock_send_verify.assert_called_once()
    
    
@pytest.mark.asyncio
async def test_request_email_already_confirmed(client: TestClient, mock_redis_only):
    """
    Tests email request for an already confirmed user (should return a success message).
    """
    response = client.post(
        "/api/auth/request_email",
        json={"email": test_user["email"]},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Your email has already been confirmed."


# 3. Password Reset Tests

@pytest.mark.asyncio
@patch("src.api.auth.send_password_reset_email")
async def test_request_password_reset_success(
    mock_send_reset: MagicMock,
    client: TestClient, 
    mock_redis_only
):
    """
    Tests the request for a password reset email (POST /auth/request_password_reset).
    """
    response = client.post(
        "/api/auth/request_password_reset",
        json={"email": test_user["email"]}, 
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    mock_send_reset.assert_called_once()


@pytest.mark.asyncio
async def test_password_reset_success(client: TestClient, valid_email_token: str, mock_redis_only):
    """
    Tests successful password reset (POST /auth/password_reset/{token}).
    """
    new_password = "verysecurenewpassword"
    
    response = client.post(
        f"/api/auth/password_reset/{valid_email_token}",
        json={"new_password": new_password},
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    # Check that the new password works 
    login_response = client.post(
        "/api/auth/login",
        data={"username": test_user["username"], "password": new_password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    
    assert login_response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_password_reset_invalid_token(client: TestClient, mock_redis_only):
    """
    Tests password reset with an invalid token (expecting 422 Unprocessable Content).
    """
    response = client.post(
        "/api/auth/password_reset/invalid_token_string",
        json={"new_password": "testpassword"},
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY