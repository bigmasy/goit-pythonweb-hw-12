import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, UTC
from jose import jwt

# Імпорти для конфігурації та тестового користувача
from tests.conftest import test_user 
from src.conf.config import config 

# === ФІКСТУРИ ===

@pytest.fixture(scope="module")
def new_user_data():
    """Дані для нового користувача, який не існує в тестовій DB."""
    return {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "newpassword123",
    }

@pytest.fixture
def mock_redis_only():
    """Імітує лише Redis (потрібно для get_current_user), щоб змусити його звертатися до DB."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    
    with patch("redis.from_url", return_value=mock_redis):
        yield mock_redis

@pytest.fixture
def valid_email_token():
    """Створює дійсний JWT для підтвердження email (для скидання пароля)."""
    expire = datetime.now(UTC) + timedelta(minutes=20)
    to_encode = {"sub": test_user["email"], "exp": expire}
    
    token = jwt.encode(
        to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM
    )
    return token

# === ТЕСТИ ===

# 1. Тести реєстрації та логіну

@pytest.mark.asyncio
# *** КРИТИЧНЕ ВИПРАВЛЕННЯ: Патчимо функцію в модулі, де вона викликається (src.api.auth) ***
@patch("src.api.auth.send_verification_email")
async def test_register_user_success(
    mock_send_verify: MagicMock,
    client: TestClient, 
    new_user_data: dict, 
    mock_redis_only
):
    """
    Тестує успішну реєстрацію нового користувача.
    """
    response = client.post(
        "/api/auth/register",
        json=new_user_data,
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    
    # Перевірка, що фонова задача викликана
    mock_send_verify.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_duplicate_email(client: TestClient, mock_redis_only):
    """
    Тестує реєстрацію з уже існуючим email (очікуємо 409 Conflict).
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


@pytest.mark.asyncio
async def test_login_user_success(client: TestClient, mock_redis_only):
    """
    Тестує успішний логін підтвердженого користувача.
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
    Тестує логін з неправильним паролем (очікуємо 401 Unauthorized).
    """
    response = client.post(
        "/api/auth/login",
        data={"username": test_user["username"], "password": "wrongpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# 2. Тести підтвердження email та запиту на email

@pytest.mark.asyncio
async def test_confirmed_email_success(client: TestClient, valid_email_token: str, mock_redis_only):
    """
    Тестує успішне підтвердження email (очікуємо 200).
    """
    response = client.get(f"/api/auth/confirmed_email/{valid_email_token}")
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
# *** ВИПРАВЛЕНО: Патчимо функцію в модулі, де вона викликається (src.api.auth) ***
@patch("src.api.auth.send_verification_email")
async def test_request_email_success(
    mock_send_verify: MagicMock,
    client: TestClient, 
    new_user_data: dict, # Використовуємо для створення користувача
    mock_redis_only
):
    """
    Тестує повторний запит на підтвердження email.
    """
    # 1. Реєструємо нового користувача для гарантії існування в DB
    unconfirmed_data = {
        "username": "unconfirmed_req",
        "email": "unconfirmed_req@example.com",
        "password": "testpass",
    }
    # Мок send_verification_email активний, тому SMTP-помилки не буде
    client.post("/api/auth/register", json=unconfirmed_data)
    
    # Скидаємо лічильник моку, щоб рахувати тільки виклик request_email
    mock_send_verify.reset_mock() 

    # 2. Виконуємо запит request_email
    response = client.post(
        "/api/auth/request_email",
        json={"email": unconfirmed_data["email"]},
    )

    assert response.status_code == status.HTTP_200_OK
    mock_send_verify.assert_called_once()


# 3. Тести скидання пароля

@pytest.mark.asyncio
# *** ВИПРАВЛЕНО: Патчимо функцію в модулі, де вона викликається (src.api.auth) ***
@patch("src.api.auth.send_password_reset_email")
async def test_request_password_reset_success(
    mock_send_reset: MagicMock,
    client: TestClient, 
    mock_redis_only
):
    """
    Тестує запит на скидання пароля (POST /auth/request_password_reset).
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
    Тестує успішне скидання пароля (POST /auth/password_reset/{token}).
    """
    new_password = "verysecurenewpassword"
    
    response = client.post(
        f"/api/auth/password_reset/{valid_email_token}",
        json={"new_password": new_password},
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    # Перевірка, чи новий пароль працює 
    login_response = client.post(
        "/api/auth/login",
        data={"username": test_user["username"], "password": new_password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    
    assert login_response.status_code == status.HTTP_200_OK