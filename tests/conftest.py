import asyncio

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from main import app
from src.database.models import Base, User, UserRole
from src.database.db import get_db
from src.services.auth import create_access_token, get_password_hash

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
)

test_user = {
    "username": "deadpool",
    "email": "deadpool@example.com",
    "password": "12345678",
}

non_admin_user = {
    "username": "nonadmin",
    "email": "user@example.com",
    "password": "passworduser",
}

@pytest.fixture(scope="module", autouse=True)
def init_models_wrap():
    """Initializes the database, drops/creates tables, and inserts base test users (ADMIN and USER)."""
    async def init_models():
        async with engine.begin() as conn:
            # Clear and create tables
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            
        async with TestingSessionLocal() as session:
            # 1. Create ADMIN user
            hash_password_admin = get_password_hash(test_user["password"])
            admin_user = User(
                username=test_user["username"],
                email=test_user["email"],
                hashed_password=hash_password_admin,
                confirmed=True,
                avatar="https://twitter.com/gravatar",
                role=UserRole.ADMIN,
            )
            session.add(admin_user)
            
            # 2. Create NON-ADMIN user
            hash_password_user = get_password_hash(non_admin_user["password"])
            regular_user = User(
                username=non_admin_user["username"],
                email=non_admin_user["email"],
                hashed_password=hash_password_user,
                confirmed=True,
                avatar="https://twitter.com/gravatar",
                role=UserRole.USER, # Standard role
            )
            session.add(regular_user)

            await session.commit()

    asyncio.run(init_models())

@pytest.fixture(scope="module")
def client():
    # Dependency override

    async def override_get_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
            except Exception as err:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)


@pytest_asyncio.fixture(scope="module")
async def get_token():
    """Fixture to get the access token for the ADMIN user."""
    token = await create_access_token(data={"sub": test_user["username"]})
    return token

@pytest_asyncio.fixture(scope="module")
async def non_admin_token():
    """Fixture to get the access token for the regular user (USER)."""
    token = await create_access_token(data={"sub": non_admin_user["username"]})
    return token