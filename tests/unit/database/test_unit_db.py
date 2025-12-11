import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from contextlib import asynccontextmanager

from src.database.db import DatabaseSessionManager, get_db

# ------------------------------------------------------------------------------
# 1. DatabaseSessionManager.session Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
@patch('src.database.db.create_async_engine')
@patch('src.database.db.async_sessionmaker')
@patch('src.database.db.config')
async def test_session_success(mock_config, mock_sessionmaker, mock_create_engine):
    """Test successful session acquisition and close."""
    mock_config.DB_URL = "test_url"
    
    # 1. Initialize the manager (Engine and SessionMaker are mocked)
    manager = DatabaseSessionManager(url=mock_config.DB_URL)
    
    # 2. Mocking the session instance returned by _session_maker
    mock_session = AsyncMock(spec=AsyncSession)
    mock_sessionmaker.return_value.return_value = mock_session
    
    # 3. Test the context
    async with manager.session() as session:
        # Check session is correctly yielded
        assert session == mock_session
        
    # Check that rollback is NOT called on success
    mock_session.rollback.assert_not_awaited()
    # Check that session is closed
    mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
@patch('src.database.db.create_async_engine')
@patch('src.database.db.async_sessionmaker')
@patch('src.database.db.config')
async def test_session_rollback_on_sqlalchemy_error(mock_config, mock_sessionmaker, mock_create_engine):
    """Test session rollback and exception propagation on SQLAlchemyError."""
    mock_config.DB_URL = "test_url"
    
    # 1. Initialize the manager
    manager = DatabaseSessionManager(url=mock_config.DB_URL)

    # 2. Mocking the session instance
    mock_session = AsyncMock(spec=AsyncSession)
    mock_sessionmaker.return_value.return_value = mock_session
    
    # 3. Test the context that raises an error
    with pytest.raises(SQLAlchemyError) as exc_info:
        async with manager.session():
            raise SQLAlchemyError("Database connection lost")
            
    # Check exception type
    assert str(exc_info.value) == "Database connection lost"
    
    # Check that rollback was called
    mock_session.rollback.assert_awaited_once()
    # Check that session is closed
    mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
@patch('src.database.db.create_async_engine')
@patch('src.database.db.async_sessionmaker')
@patch('src.database.db.config')
async def test_session_raises_uninitialized_error(mock_config, mock_sessionmaker, mock_create_engine):
    """Test the scenario where _session_maker is None (uninitialized)."""
    
    mock_config.DB_URL = "test_url"
    
    # 1. Initialize the manager
    manager = DatabaseSessionManager(url=mock_config.DB_URL)
    
    # 2. Manually set _session_maker to None (to simulate failure)
    manager._session_maker = None
    
    # 3. Test the context
    with pytest.raises(Exception) as exc_info:
        async with manager.session():
            pass # Should not be reached
            
    assert str(exc_info.value) == "Database session is not initialized"


# ------------------------------------------------------------------------------
# 2. get_db Dependency Test
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
@patch('src.database.db.sessionmanager')
async def test_get_db_dependency(mock_manager):
    """Test the get_db dependency ensures session management is used."""
    
    # Mock the session context manager method to yield a mock session
    mock_session = AsyncMock(spec=AsyncSession)
    
    @asynccontextmanager
    async def mock_session_context():
        yield mock_session

    mock_manager.session.return_value = mock_session_context()

    # Test the generator (yield)
    db_generator = get_db()
    
    # Get the yielded session
    result = await anext(db_generator) 
    assert result == mock_session
    
    # Attempt to close the generator (finally block in get_db)
    with pytest.raises(StopAsyncIteration):
        await anext(db_generator)
            
    # Check that session() was called on the manager
    mock_manager.session.assert_called_once()