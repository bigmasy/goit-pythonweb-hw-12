import pytest
from unittest.mock import MagicMock, patch
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from io import BytesIO

# Імпортуємо test_user, client, get_token зі спільного conftest
# та інші необхідні об'єкти
from src.database.models import User
from src.database.db import get_db

# Припускаємо, що status імпортується у вашому коді або доступний
# через стандартний імпорт fastapi

# Ваші фікстури client, get_token, та test_user повинні бути доступні
# завдяки conftest.py, якщо pytest їх автоматично знаходить.


### 1. Тест маршруту /users/me

def test_me_success(client: TestClient, get_token: str):
    """
    Тестує успішний запит до /users/me з дійсним токеном.
    """
    headers = {"Authorization": f"Bearer {get_token}"}
    response = client.get("/api/users/me", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Перевіряємо, що повернуті дані користувача відповідають тестовому користувачу
    assert data["username"] == "deadpool"
    assert data["email"] == "deadpool@example.com"
    assert "id" in data
    assert "avatar" in data


def test_me_unauthorized(client: TestClient):
    """
    Тестує запит до /users/me без токена (неавторизований доступ).
    """
    # Запит без заголовка Authorization
    response = client.get("/api/users/me")

    # Очікується 401 Unauthorized
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


# Примітка: Тестування лімітера (slowapi) вимагає складнішого налаштування, 
# включаючи імітацію декількох запитів за короткий час. 
# Зазвичай це робиться окремо або ігнорується у простих юніт-тестах.
@pytest.mark.asyncio
@patch("src.services.upload_file.UploadFileService.upload_file")
@patch("redis.from_url") # <--- ДОДАНО: Імітація підключення до Redis
async def test_update_avatar_success(
    mock_redis_from_url: MagicMock, # <--- Новий аргумент для імітованого Redis
    mock_upload_file: MagicMock, 
    client: TestClient, 
    get_token: str, 
    init_models_wrap
):
    """
    Тестує успішне оновлення аватара. Імітує Cloudinary API та Redis.
    """
    # 1. Налаштування імітації Redis
    mock_redis = MagicMock()
    
    # Говоримо, що redis.from_url повинен повернути наш імітований об'єкт
    mock_redis_from_url.return_value = mock_redis
    
    # Говоримо, що метод get() на нашому імітованому Redis повинен повернути None
    # Це змусить get_current_user ЗВЕРНУТИСЯ ДО БАЗИ ДАНИХ, щоб отримати актуальну роль
    mock_redis.get.return_value = None 
    
    # 2. Налаштування імітації Cloudinary
    test_avatar_url = "https://new-avatar.example.com/deadpool_new"
    mock_upload_file.return_value = test_avatar_url

    headers = {"Authorization": f"Bearer {get_token}"}
    test_file_content = b"fake image content"
    
    # 3. Виконання запиту
    response = client.patch(
        "/api/users/avatar",
        headers=headers,
        files={"file": ("test.jpg", BytesIO(test_file_content), "image/jpeg")},
    )

    # 4. Перевірка
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["avatar"] == test_avatar_url
    
    # Перевірка, що Redis.get був викликаний, але повернув None
    mock_redis.get.assert_called_once()
    
    # Перевірка, що користувач був записаний назад у кеш
    mock_redis.set.assert_called_once()