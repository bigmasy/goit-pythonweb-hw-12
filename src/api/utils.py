from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.database.db import get_db

router = APIRouter(tags=["utils"])


@router.get("/healthchecker")
async def healthchecker(db: AsyncSession = Depends(get_db)):
    """
    Performs a health check on the API and the underlying database connection.

    It executes a simple database query (SELECT 1) to ensure the connection
    is active and correctly configured.

    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :raises HTTPException: 500 Internal Server Error if the database connection fails
                           or returns an unexpected result.
    :return: A success message indicating the API is operational.
    :rtype: dict
    """
    try:
        # Execute an asynchronous query to check database connectivity
        result = await db.execute(text("SELECT 1"))
        result = result.scalar_one_or_none()

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database is not configured correctly",
            )
        return {"message": "Welcome to FastAPI!"}
    except Exception as e:
        # Log the exception for debugging (optional, but useful)
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error connecting to the database",
        )