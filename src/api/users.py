from fastapi import APIRouter, Depends, Request, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas import UserResponse
from src.services.auth import get_current_user, get_admin_user
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.schemas import UserResponse
from src.database.models import User
from src.database.db import get_db
from src.services.upload_file import UploadFileService
from src.conf.config import config
from src.services.users import UserService


router = APIRouter(prefix="/users", tags=["users"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/me", response_model=UserResponse, description="No more than 10 requests per minute")
@limiter.limit("10/minute")
async def me(request: Request, user: UserResponse = Depends(get_current_user)):
    """
    Retrieves the information of the currently authenticated user.

    The route is protected by a rate limit of 10 requests per minute per IP address.

    :param request: The incoming request object (used by the limiter).
    :type request: :class:`fastapi.Request`
    :param user: The current authenticated user object obtained via dependency injection.
    :type user: :class:`src.schemas.UserResponse`
    :return: The user's detailed information.
    :rtype: :class:`src.schemas.UserResponse`
    """
    return user


@router.patch("/avatar", response_model=UserResponse)
async def update_avatar_user(
    file: UploadFile = File(),
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Uploads a new avatar file for the current user and updates the user's avatar URL in the database.

    Note: This endpoint currently uses ``get_admin_user`` for authentication, restricting
    avatar updates to admin users only, based on the provided code structure.

    :param file: The avatar image file to be uploaded.
    :type file: :class:`fastapi.UploadFile`
    :param user: The authenticated user object (must be an admin based on dependency).
    :type user: :class:`src.database.models.User`
    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :return: The user object with the newly updated avatar URL.
    :rtype: :class:`src.schemas.UserResponse`
    """
    upload_service = UploadFileService(
        config.CLD_NAME, config.CLD_API_KEY, config.CLD_API_SECRET
    )
    avatar_url = upload_service.upload_file(file, user.username)

    user_service = UserService(db)
    user = await user_service.update_avatar_url(user.email, avatar_url)

    return user