import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from main import app
from src.database.db import get_db


def test_healthchecker_success(client: TestClient):
    """
    Tests successful request to the /healthchecker route when the 
    database connection is operational (using the test DB from conftest).
    """
    # Execute the GET request to /api/healthchecker
    response = client.get("/api/healthchecker")

    # Check response status: Expect HTTP 200 OK
    assert response.status_code == status.HTTP_200_OK

    # Check response body
    expected_response = {"message": "Welcome to FastAPI!"}
    assert response.json() == expected_response


@pytest.mark.asyncio
@patch("src.api.utils.get_db")
async def test_healthchecker_db_connection_error(mock_get_db: MagicMock, client: TestClient):
    """
    Tests health check when the database connection fails or encounters an error. 
    Expect 500 Internal Server Error.
    """
    # 1. Mock the DB session to raise SQLAlchemyError upon execution
    mock_db_session = MagicMock(spec=AsyncSession)
    mock_db_session.execute.side_effect = SQLAlchemyError("DB connection failed during SELECT")

    # 2. Create an override generator that yields the failing session
    async def override_get_db_error() -> AsyncGenerator[AsyncSession, None]:
        yield mock_db_session

    # 3. Apply the dependency override
    app.dependency_overrides[get_db] = override_get_db_error

    try:
        # 4. Execute the request
        response = client.get("/api/healthchecker")

        # 5. Assertions
        # The router should catch the exception and return 500
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Error connecting to the database"

    finally:
        # 6. Cleanup: Restore the original dependency
        app.dependency_overrides[get_db] = get_db