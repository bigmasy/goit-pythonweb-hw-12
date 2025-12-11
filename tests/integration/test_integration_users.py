import pytest
from unittest.mock import MagicMock, patch
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from io import BytesIO

# Imports (assuming dependencies are available via conftest)
from src.database.models import User
from src.database.db import get_db
# test_user, get_token, and non_admin_token are assumed to be fixtures from conftest.py


# === FIXTURES ===

@pytest.fixture(scope="function")
def admin_headers(get_token: str):
    """Fixture for authentication headers with ADMIN role permissions."""
    return {"Authorization": f"Bearer {get_token}"}

@pytest.fixture(scope="function")
def user_headers(non_admin_token: str):
    """Fixture for authentication headers with regular USER role permissions."""
    return {"Authorization": f"Bearer {non_admin_token}"}

# === TESTS ===

# 1. /users/me Route Tests

def test_me_success(client: TestClient, admin_headers: dict):
    """
    Tests successful request to /users/me with a valid token.
    """
    response = client.get("/api/users/me", headers=admin_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["username"] == "deadpool"
    assert data["email"] == "deadpool@example.com"


def test_me_unauthorized(client: TestClient):
    """
    Tests request to /users/me without a token (unauthorized access).
    """
    response = client.get("/api/users/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_me_invalid_token(client: TestClient):
    """
    Tests request to /users/me with an invalid token (401 Unauthorized).
    """
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    response = client.get("/api/users/me", headers=headers)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Could not validate credentials"


# 2. Avatar Update Tests (PATCH /users/avatar)

@pytest.mark.asyncio
@patch("src.services.upload_file.UploadFileService.upload_file")
@patch("redis.from_url") 
async def test_update_avatar_success(
    mock_redis_from_url: MagicMock, 
    mock_upload_file: MagicMock, 
    client: TestClient, 
    admin_headers: dict, 
    init_models_wrap
):
    """
    Tests successful avatar update (for an authorized user).
    Assumes the user is either ADMIN or has the required permissions.
    """
    mock_redis = MagicMock()
    mock_redis_from_url.return_value = mock_redis
    mock_redis.get.return_value = None 
    
    test_avatar_url = "https://new-avatar.example.com/deadpool_new"
    mock_upload_file.return_value = test_avatar_url

    test_file_content = b"fake image content"
    
    response = client.patch(
        "/api/users/avatar",
        headers=admin_headers,
        files={"file": ("test.jpg", BytesIO(test_file_content), "image/jpeg")},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["avatar"] == test_avatar_url
    
    mock_redis.set.assert_called_once()


@pytest.mark.asyncio
@patch("src.services.upload_file.UploadFileService.upload_file")
@patch("redis.from_url") 
async def test_update_avatar_forbidden(
    mock_redis_from_url: MagicMock, 
    mock_upload_file: MagicMock, 
    client: TestClient, 
    user_headers: dict, 
    init_models_wrap
):
    """
    Tests avatar update by a regular user (non-admin). Expect 403 Forbidden.
    """
    mock_redis = MagicMock()
    mock_redis_from_url.return_value = mock_redis
    mock_redis.get.return_value = None 
    
    test_file_content = b"fake image content"
    
    response = client.patch(
        "/api/users/avatar",
        headers=user_headers,
        files={"file": ("test.jpg", BytesIO(test_file_content), "image/jpeg")},
    )

    # get_admin_user dependency should return 403
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Allowed only for Admin"


@pytest.mark.asyncio
@patch("src.services.upload_file.UploadFileService.upload_file")
async def test_update_avatar_unauthorized(mock_upload_file: MagicMock, client: TestClient):
    """
    Tests avatar update without a token. Expect 401 Unauthorized.
    """
    test_file_content = b"fake image content"
    
    response = client.patch(
        "/api/users/avatar",
        files={"file": ("test.jpg", BytesIO(test_file_content), "image/jpeg")},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED