import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from sqlalchemy.ext.asyncio import create_async_engine
from src.database.models import Base
from src.conf.config import config

async def create_tables():
    """
    Creates all tables defined in SQLAlchemy Base using the application's configuration.
    This script is run by the 'migrator' service in Docker Compose.
    """
    
    db_url = config.DB_URL
    engine = create_async_engine(db_url, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("Database tables created successfully!")

if __name__ == "__main__":
    try:
        asyncio.run(create_tables())
    except Exception as e:
        print(f"Error creating database tables: {e}")
        sys.exit(1)