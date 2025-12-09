from fastapi import APIRouter, Depends, HTTPException, status, Security, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
from src.schemas import UserCreate, TokenSchema, UserResponse, RequestEmail, RequestPasswordReset, PasswordReset
from src.services.auth import create_access_token, get_password_hash, verify_password, get_email_from_token
from src.services.users import UserService
from src.database.db import get_db
from src.services.email import send_verification_email, send_password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, background_tasks: BackgroundTasks, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Registers a new user in the system.

    If the email or username already exists, it raises a 409 Conflict error.
    It hashes the user's password and sends a verification email in the background.

    :param user_data: The user registration data.
    :type user_data: :class:`src.schemas.UserCreate`
    :param background_tasks: Background tasks object for sending emails.
    :type background_tasks: :class:`fastapi.BackgroundTasks`
    :param request: The request object to get the base URL.
    :type request: :class:`fastapi.Request`
    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :raises HTTPException: 409 Conflict if user with email or username already exists.
    :return: The newly created user object.
    :rtype: :class:`src.schemas.UserResponse`
    """
    user_service = UserService(db)

    email_user = await user_service.get_user_by_email(user_data.email)
    if email_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists.",
        )

    username_user = await user_service.get_user_by_username(user_data.username)
    if username_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with that name already exists.",
        )
    user_data.password = get_password_hash(user_data.password)
    new_user = await user_service.create_user(user_data)
    background_tasks.add_task(send_verification_email, new_user.email, new_user.username, request.base_url)
    return new_user


@router.post("/login", response_model=TokenSchema)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    Authenticates a user and generates an access token.

    Verifies the username and password against the database. Requires email confirmation.

    :param form_data: The username and password provided in the OAuth2 form.
    :type form_data: :class:`fastapi.security.OAuth2PasswordRequestForm`
    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :raises HTTPException: 401 Unauthorized if login/password is incorrect or email is not confirmed.
    :return: An object containing the access token and token type.
    :rtype: :class:`src.schemas.TokenSchema`
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email address not confirmed",
        )

    access_token = await create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):
    """
    Confirms the user's email address using a verification token.

    Decodes the token to get the user's email and updates the user's confirmation status.

    :param token: The email verification token.
    :type token: str
    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :raises HTTPException: 400 Bad Request if the token is invalid or user is not found.
    :return: A message indicating the confirmation status.
    :rtype: dict
    """
    email = await get_email_from_token(token)
    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        return {"message": "Your email has already been confirmed."}
    await user_service.confirmed_email(email)
    return {"message": "Email confirmed"}


@router.post("/request_email")
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Requests a new email verification link if the user's email is not confirmed.

    Sends a new verification email in the background if the user exists and is not confirmed.

    :param body: The request body containing the user's email.
    :type body: :class:`src.schemas.RequestEmail`
    :param background_tasks: Background tasks object for sending emails.
    :type background_tasks: :class:`fastapi.BackgroundTasks`
    :param request: The request object to get the base URL.
    :type request: :class:`fastapi.Request`
    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :return: A message instructing the user to check their email.
    :rtype: dict
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_email(body.email)

    if user.confirmed:
        return {"message": "Your email has already been confirmed."}
    if user:
        background_tasks.add_task(
            send_verification_email, user.email, user.username, request.base_url
        )
    return {"message": "Check your email for confirmation."}


@router.post("/request_password_reset")
async def request_password_reset(
    body: RequestPasswordReset,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Requests a password reset link for the user's email.

    Sends a password reset email in the background.

    :param body: The request body containing the user's email.
    :type body: :class:`src.schemas.RequestPasswordReset`
    :param background_tasks: Background tasks object for sending emails.
    :type background_tasks: :class:`fastapi.BackgroundTasks`
    :param request: The request object to get the base URL.
    :type request: :class:`fastapi.Request`
    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :return: A message instructing the user to check their email.
    :rtype: dict
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_email(body.email)
    background_tasks.add_task(send_password_reset_email, user.email, user.username, request.base_url)
    return {"message": "Check your email for confirmation."}


@router.post("/password_reset/{token}")
async def password_reset(body: PasswordReset, token: str, db: AsyncSession = Depends(get_db)):
    """
    Sets a new password for the user using a password reset token.

    Decodes the token to get the user's email, verifies the user, and updates the password.

    :param body: The request body containing the new password.
    :type body: :class:`src.schemas.PasswordReset`
    :param token: The password reset token.
    :type token: str
    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :raises HTTPException: 400 Bad Request if the token is invalid or user is not found.
    :return: The user object with the updated password (hash).
    :rtype: The return type of ``UserService.set_new_password``.
    """
    email = await get_email_from_token(token)
    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    new_password_hash = get_password_hash(body.new_password)
    return await user_service.set_new_password(email=email, new_password_hash=new_password_hash)