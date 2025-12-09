from pathlib import Path

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import EmailStr

from src.services.auth import create_email_token
from src.conf.config import config

conf = ConnectionConfig(
    MAIL_USERNAME=config.MAIL_USERNAME,
    MAIL_PASSWORD=config.MAIL_PASSWORD,
    MAIL_FROM=config.MAIL_FROM,
    MAIL_PORT=config.MAIL_PORT,
    MAIL_SERVER=config.MAIL_SERVER,
    MAIL_FROM_NAME=config.MAIL_FROM_NAME,
    MAIL_STARTTLS=config.MAIL_STARTTLS,
    MAIL_SSL_TLS=config.MAIL_SSL_TLS,
    USE_CREDENTIALS=config.USE_CREDENTIALS,
    VALIDATE_CERTS=config.VALIDATE_CERTS,
    TEMPLATE_FOLDER=Path(__file__).parent / "templates",
)
"""
Configuration object for connecting to the SMTP server using fastapi-mail.

All settings are loaded from the application configuration.
The TEMPLATE_FOLDER is set relative to the current file location to find
email HTML templates.
:meta type: :class:`fastapi_mail.ConnectionConfig`
"""

async def send_verification_email(email: EmailStr, username: str, host: str):
    """
    Sends an email to the user containing a link for email verification.

    Generates a time-limited token and uses the 'verify_email.html' template.

    :param email: The recipient's email address.
    :type email: :class:`pydantic.EmailStr`
    :param username: The recipient's username for personalization.
    :type username: str
    :param host: The base URL of the application to construct the verification link.
    :type host: str
    :raises ConnectionErrors: If there is an issue connecting to the mail server.
    :return: None
    :rtype: None
    """
    try:
        token_verification = create_email_token({"sub": email})
        message = MessageSchema(
            subject="Confirm your email",
            recipients=[email],
            template_body={
                "host": host,
                "username": username,
                "token": token_verification,
            },
            subtype=MessageType.html,
        )

        fm = FastMail(conf)
        await fm.send_message(message, template_name="verify_email.html")
    except ConnectionErrors as err:
        print(err)

async def send_password_reset_email(email: EmailStr, username: str, host: str):
    """
    Sends an email to the user containing a link for password reset confirmation.

    Generates a time-limited token and uses the 'reset_password.html' template.

    :param email: The recipient's email address.
    :type email: :class:`pydantic.EmailStr`
    :param username: The recipient's username for personalization.
    :type username: str
    :param host: The base URL of the application to construct the reset link.
    :type host: str
    :raises ConnectionErrors: If there is an issue connecting to the mail server.
    :return: None
    :rtype: None
    """
    try:
        token_verification = create_email_token({"sub": email})
        message = MessageSchema(
            subject="Password reset",
            recipients=[email],
            template_body={
                "host": host,
                "username": username,
                "token": token_verification,
            },
            subtype=MessageType.html,
        )

        fm = FastMail(conf)
        await fm.send_message(message, template_name="reset_password.html")
    except ConnectionErrors as err:
        print(err)