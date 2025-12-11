import pytest
from fastapi import status
from fastapi.testclient import TestClient
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from src.services.contacts import DuplicateContactError 

# Data for creating a test contact
test_contact_data = {
    "first_name": "Wade",
    "last_name": "Wilson",
    "email": "wade.wilson@xforce.com",
    "phone_number": "555-1234-567",
    "birthday": str(date.today() - timedelta(days=365 * 30)),
    "additional_data": "Merc with a mouth."
}

# Variable to store the contact ID (used across tests)
CONTACT_ID = None

@pytest.fixture(scope="function")
def headers(get_token: str):
    """Fixture for authentication headers."""
    return {"Authorization": f"Bearer {get_token}"}

@pytest.fixture(scope="function")
def invalid_headers():
    """Fixture for invalid authentication headers."""
    return {"Authorization": f"Bearer invalid_token_format"}


### 1. Create Tests (POST)

@pytest.mark.asyncio
@patch("redis.from_url") 
async def test_create_contact_success(mock_redis_from_url: MagicMock, client: TestClient, headers: dict):
    """
    Tests successful creation of a new contact (POST /api/contacts/). Expect 201.
    """
    mock_redis = MagicMock()
    mock_redis_from_url.return_value = mock_redis
    mock_redis.get.return_value = None

    global CONTACT_ID
    
    response = client.post(
        "/api/contacts/",
        json=test_contact_data,
        headers=headers
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    
    # Store ID for use in other tests
    CONTACT_ID = data["id"]


@pytest.mark.asyncio
@patch("redis.from_url")
# Patch the repository method that raises DuplicateContactError
@patch("src.repository.contacts.ContactRepository.create_contact") 
async def test_create_contact_duplicate(
    mock_create_contact_repo: MagicMock, 
    mock_redis_from_url: MagicMock, 
    client: TestClient, 
    headers: dict
):
    """
    Tests creation with duplicate email/phone data. Expect 409 Conflict.
    (Mocks the repository exception).
    """
    mock_redis = MagicMock()
    mock_redis_from_url.return_value = mock_redis
    mock_redis.get.return_value = None

    # Force the mocked method to raise the expected exception
    mock_create_contact_repo.side_effect = DuplicateContactError(
        message="Contact with this email already exists."
    )

    response = client.post(
        "/api/contacts/", 
        json=test_contact_data,
        headers=headers
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Contact with this email already exists."


@pytest.mark.asyncio
async def test_create_contact_unauthorized(client: TestClient):
    """
    Tests request to create a contact without authorization. Expect 401 Unauthorized.
    """
    response = client.post(
        "/api/contacts/",
        json=test_contact_data,
        headers={"Authorization": "Bearer "}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Could not validate credentials"


### 2. Read Tests (GET)

@pytest.mark.asyncio
@patch("redis.from_url")
async def test_read_contacts_success(mock_redis_from_url: MagicMock, client: TestClient, headers: dict):
    """
    Tests successful retrieval of the contact list (GET /api/contacts/).
    """
    mock_redis = MagicMock()
    mock_redis_from_url.return_value = mock_redis
    mock_redis.get.return_value = None
    
    response = client.get(
        "/api/contacts/",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.asyncio
@patch("redis.from_url")
async def test_read_contact_by_id_success(mock_redis_from_url: MagicMock, client: TestClient, headers: dict):
    """
    Tests successful retrieval of a contact by ID (GET /api/contacts/{contact_id}).
    """
    mock_redis = MagicMock()
    mock_redis_from_url.return_value = mock_redis
    mock_redis.get.return_value = None
    
    assert CONTACT_ID is not None
    
    response = client.get(
        f"/api/contacts/{CONTACT_ID}",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == CONTACT_ID


@pytest.mark.asyncio
@patch("redis.from_url")
async def test_read_contact_by_id_not_found(mock_redis_from_url: MagicMock, client: TestClient, headers: dict):
    """
    Tests retrieval of a non-existent contact by ID (expect 404).
    """
    mock_redis = MagicMock()
    mock_redis_from_url.return_value = mock_redis
    mock_redis.get.return_value = None
    
    non_existent_id = 99999
    response = client.get(
        f"/api/contacts/{non_existent_id}",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Contact not found"


@pytest.mark.asyncio
@patch("redis.from_url")
async def test_search_contacts_by_name(mock_redis_from_url: MagicMock, client: TestClient, headers: dict):
    """
    Tests searching for a contact by name (GET /api/contacts/search?query=...).
    """
    mock_redis = MagicMock()
    mock_redis_from_url.return_value = mock_redis
    mock_redis.get.return_value = None
    
    search_query = "Wade"
    response = client.get(
        f"/api/contacts/search?query={search_query}",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    if data:
        assert data[0]["first_name"] == "Wade"
    
@pytest.mark.asyncio
async def test_read_contact_by_id_unauthorized(client: TestClient, headers: dict):
    """
    Tests request to read a contact with an invalid token. Expect 401.
    """
    response = client.get(f"/api/contacts/{CONTACT_ID}", headers={"Authorization": "Bearer wrong_token"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Could not validate credentials"


### 3. Update and Delete Tests (PUT/DELETE)

@pytest.mark.asyncio
@patch("redis.from_url")
async def test_update_contact_success(mock_redis_from_url: MagicMock, client: TestClient, headers: dict):
    """
    Tests successful contact update (PUT /api/contacts/{contact_id}).
    """
    mock_redis = MagicMock()
    mock_redis_from_url.return_value = mock_redis
    mock_redis.get.return_value = None
    
    assert CONTACT_ID is not None
    
    updated_data = {
        "first_name": "Deadpool", 
        "last_name": "Wilson",
        "email": "wade.wilson@xforce.com",
        "phone_number": "555-1234-567",
        "birthday": str(date.today() - timedelta(days=365*30)),
        "additional_data": "Updated note."
    }
    
    response = client.put(
        f"/api/contacts/{CONTACT_ID}",
        json=updated_data,
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == CONTACT_ID
    assert data["first_name"] == updated_data["first_name"]


@pytest.mark.asyncio
@patch("redis.from_url")
@patch("src.repository.contacts.ContactRepository.update_contact") 
async def test_update_contact_duplicate_conflict(
    mock_update_contact_repo: MagicMock,
    mock_redis_from_url: MagicMock, 
    client: TestClient, 
    headers: dict
):
    """
    Tests contact update resulting in duplicate email/phone. Expect 409 Conflict.
    (Mocks the repository method to raise DuplicateContactError).
    """
    mock_redis = MagicMock()
    mock_redis_from_url.return_value = mock_redis
    mock_redis.get.return_value = None

    # Force the mocked method to raise the expected exception
    mock_update_contact_repo.side_effect = DuplicateContactError(
        message="Contact with this phone number already exists."
    )

    update_data = {"phone_number": "555-999-999"}

    response = client.put(
        f"/api/contacts/{CONTACT_ID}",
        json=update_data,
        headers=headers
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Contact with this phone number already exists."


@pytest.mark.asyncio
@patch("redis.from_url")
async def test_update_contact_not_found(mock_redis_from_url: MagicMock, client: TestClient, headers: dict):
    """
    Tests updating a non-existent contact. Expect 404.
    """
    mock_redis = MagicMock()
    mock_redis_from_url.return_value = mock_redis
    mock_redis.get.return_value = None
    
    non_existent_id = 99999
    update_data = {"first_name": "NonExist"}
    
    response = client.put(
        f"/api/contacts/{non_existent_id}",
        json=update_data,
        headers=headers
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Contact not found"


@pytest.mark.asyncio
async def test_update_contact_unauthorized(client: TestClient, headers: dict):
    """
    Tests request to update a contact with an invalid token. Expect 401.
    """
    response = client.put(
        f"/api/contacts/{CONTACT_ID}",
        json={"first_name": "Unauthorized"},
        headers={"Authorization": "Bearer wrong_token"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.asyncio
@patch("redis.from_url")
async def test_delete_contact_success(mock_redis_from_url: MagicMock, client: TestClient, headers: dict):
    """
    Tests successful contact deletion (DELETE /api/contacts/{contact_id}).
    """
    mock_redis = MagicMock()
    mock_redis_from_url.return_value = mock_redis
    mock_redis.get.return_value = None
    
    assert CONTACT_ID is not None
    
    response = client.delete(
        f"/api/contacts/{CONTACT_ID}",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == CONTACT_ID
    
    # Check if contact is truly deleted
    response_get = client.get(f"/api/contacts/{CONTACT_ID}", headers=headers)
    assert response_get.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("redis.from_url")
async def test_delete_contact_not_found(mock_redis_from_url: MagicMock, client: TestClient, headers: dict):
    """
    Tests deletion of a non-existent contact (expect 404).
    """
    mock_redis = MagicMock()
    mock_redis_from_url.return_value = mock_redis
    mock_redis.get.return_value = None
    
    non_existent_id = 99999
    response = client.delete(
        f"/api/contacts/{non_existent_id}",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_contact_unauthorized(client: TestClient, headers: dict):
    """
    Tests request to delete a contact with an invalid token. Expect 401.
    """
    # Use an invalid token
    response = client.delete(
        f"/api/contacts/{CONTACT_ID}", 
        headers={"Authorization": "Bearer wrong_token"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Could not validate credentials"