from datetime import datetime, timedelta, UTC
from typing import Optional

from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext
import bcrypt
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from src.database.db import get_db
from src.database.models import UserRole
from src.conf.config import config
from src.services.users import UserService
import pickle
import redis
from logging import getLogger

logger = getLogger(__name__)

pwd_context = CryptContext(
    schemes=["bcrypt_sha256"],
    default="bcrypt_sha256",
    deprecated="auto",
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a hashed password using bcrypt.

    :param plain_password: The password provided by the user (plain text).
    :type plain_password: str
    :param hashed_password: The hashed password stored in the database.
    :type hashed_password: str
    :return: True if the passwords match, False otherwise.
    :rtype: bool
    """
    password = plain_password.encode("utf-8")
    hashed = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password, hashed)


def get_password_hash(password: str) -> str:
    """
    Generates a secure hash for a given password using bcrypt.

    :param password: The plain-text password to hash.
    :type password: str
    :return: The generated password hash string.
    :rtype: str
    """
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(14))
    return hashed.decode("utf-8")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def create_access_token(data: dict, expires_delta: Optional[int] = None):
    """
    Creates a new JWT access token based on provided data.

    The token includes an expiration time (exp).

    :param data: The payload data to encode (e.g., {"sub": user_email}).
    :type data: dict
    :param expires_delta: Optional override for token expiration time in seconds.
    :type expires_delta: int | None
    :return: The encoded JWT access token.
    :rtype: str
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + timedelta(seconds=expires_delta)
    else:
        expire = datetime.now(UTC) + timedelta(seconds=config.JWT_EXPIRATION_SECONDS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM
    )
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    """
    Dependency function to retrieve and authenticate the current user from an access token.

    Decodes the JWT, retrieves the user from Redis cache (or database if not cached),
    and validates credentials. Caches the user for subsequent requests.

    :param token: The JWT token provided in the Authorization header.
    :type token: str
    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :raises HTTPException: 401 Unauthorized if the token is invalid or the user is not found.
    :return: The authenticated User object.
    :rtype: :class:`src.database.models.User`
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
        username = payload["sub"]
        if username is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception

    r = redis.from_url(config.REDIS_URL)
    user = r.get(payload["sub"])
    if user:
        logger.info("Get user from cache")
        return pickle.loads(user)
    user_service = UserService(db)
    user = await user_service.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    r.set(payload["sub"], pickle.dumps(user))
    r.expire(payload["sub"], 3600)
    logger.info('Write user to cashe')
    return user


def create_email_token(data: dict):
    """
    Creates a time-limited JWT token specifically for email verification or password reset.

    The token is valid for 20 minutes.

    :param data: The payload data to encode (e.g., {"sub": user_email}).
    :type data: dict
    :return: The encoded email verification token.
    :rtype: str
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=20)
    to_encode.update({"iat": datetime.now(UTC), "exp": expire})
    token = jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    return token

async def get_email_from_token(token: str):
    """
    Decodes an email verification token and extracts the user's email address.

    :param token: The email verification token.
    :type token: str
    :raises HTTPException: 422 Unprocessable Content if the token is invalid or expired.
    :return: The email address stored in the token's payload ("sub" field).
    :rtype: str
    """
    try:
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
        email = payload["sub"]
        return email
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid email verification token",
        )


async def get_admin_user(current_user = Depends(get_current_user)):
    """
    Dependency function that checks if the current authenticated user has the 'admin' role.

    This function relies on `get_current_user` to authenticate first.

    :param current_user: The authenticated user object provided by `get_current_user`.
    :type current_user: :class:`src.database.models.User`
    :raises HTTPException: 403 Forbidden if the user's role is not 'admin'.
    :return: The authenticated User object if they are an admin.
    :rtype: :class:`src.database.models.User`
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Allowed only for Admin')
    return current_user