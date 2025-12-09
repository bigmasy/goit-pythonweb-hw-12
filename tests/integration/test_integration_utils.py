import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Імпортуємо залежності, необхідні для тесту збоїв
from main import app
from src.database.db import get_db

def test_healthchecker_success(client: TestClient):
    """
    Тестує успішний запит до маршруту /healthchecker, 
    коли з'єднання з базою даних працює (використовуючи тестову DB з conftest).
    """
    # 1. Виконання запиту GET до /healthchecker
    response = client.get("/api/healthchecker")

    # 2. Перевірка статусу відповіді: Очікується HTTP 200 OK
    assert response.status_code == status.HTTP_200_OK

    # 3. Перевірка тіла відповіді
    expected_response = {"message": "Welcome to FastAPI!"}
    assert response.json() == expected_response

