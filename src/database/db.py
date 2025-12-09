import contextlib

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from src.conf.config import config

class DatabaseSessionManager:
    """
    Manages asynchronous database connections and session creation using SQLAlchemy.

    It initializes an AsyncEngine and an async_sessionmaker, and provides a context
    manager for safely acquiring and releasing database sessions.
    """
    def __init__(self, url: str):
        """
        Initializes the DatabaseSessionManager.

        :param url: The asynchronous connection URL for the database.
        :type url: str
        """
        self._engine: AsyncEngine | None = create_async_engine(url)
        self._session_maker: async_sessionmaker = async_sessionmaker(
            autoflush=False, autocommit=False, bind=self._engine
        )

    @contextlib.asynccontextmanager
    async def session(self):
        """
        Provides an asynchronous context manager for a database session.

        The session is created upon entering the context and automatically closed
        upon exit. If a :class:`sqlalchemy.exc.SQLAlchemyError` occurs within the
        context, a rollback is performed before re-raising the exception.

        :raises Exception: If the database session maker is not initialized.
        :raises SQLAlchemyError: If any database error occurs during the context execution.
        :yield: An asynchronous database session.
        :rtype: :class:`sqlalchemy.ext.asyncio.AsyncSession`
        """
        if self._session_maker is None:
            raise Exception("Database session is not initialized")
        session = self._session_maker()
        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            raise  # Re-raise the original error
        finally:
            await session.close()

sessionmanager = DatabaseSessionManager(config.DB_URL)

async def get_db():
    """
    FastAPI dependency function to provide a database session.

    This function uses the :meth:`DatabaseSessionManager.session` context manager
    to safely yield an async session, ensuring it is properly closed after the
    request is finished.

    :yield: An asynchronous database session object.
    :rtype: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    """
    async with sessionmanager.session() as session:
        yield session