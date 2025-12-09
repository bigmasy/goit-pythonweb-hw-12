from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr

class Settings(BaseSettings):
    """
    Configuration settings for the application loaded from environment variables
    or a .env file using Pydantic's BaseSettings.

    :ivar DB_URL: Database connection URL.
    :vartype DB_URL: str
    :ivar REDIS_URL: Redis server connection URL.
    :vartype REDIS_URL: str
    :ivar JWT_SECRET: Secret key for JWT token encoding.
    :vartype JWT_SECRET: str
    :ivar JWT_ALGORITHM: Algorithm used for JWT encoding (e.g., "HS256").
    :vartype JWT_ALGORITHM: str
    :ivar JWT_EXPIRATION_SECONDS: Lifetime of the access token in seconds.
    :vartype JWT_EXPIRATION_SECONDS: int
    :ivar MAIL_USERNAME: Email account username for sending emails.
    :vartype MAIL_USERNAME: :class:`pydantic.EmailStr`
    :ivar MAIL_PASSWORD: Email account password.
    :vartype MAIL_PASSWORD: str
    :ivar MAIL_FROM: Sender email address.
    :vartype MAIL_FROM: :class:`pydantic.EmailStr`
    :ivar MAIL_PORT: SMTP server port.
    :vartype MAIL_PORT: int
    :ivar MAIL_SERVER: SMTP server host address.
    :vartype MAIL_SERVER: str
    :ivar MAIL_FROM_NAME: Display name for the sender.
    :vartype MAIL_FROM_NAME: str
    :ivar MAIL_STARTTLS: Enable/Disable STARTTLS security protocol.
    :vartype MAIL_STARTTLS: bool
    :ivar MAIL_SSL_TLS: Enable/Disable SSL/TLS security protocol.
    :vartype MAIL_SSL_TLS: bool
    :ivar USE_CREDENTIALS: Flag to indicate if credentials should be used.
    :vartype USE_CREDENTIALS: bool
    :ivar VALIDATE_CERTS: Flag to indicate if SMTP server certificates should be validated.
    :vartype VALIDATE_CERTS: bool
    :ivar CLD_NAME: Cloudinary cloud name.
    :vartype CLD_NAME: str
    :ivar CLD_API_KEY: Cloudinary API key.
    :vartype CLD_API_KEY: int
    :ivar CLD_API_SECRET: Cloudinary API secret.
    :vartype CLD_API_SECRET: str
    """
    # --- Database & Caching ---
    DB_URL: str = "postgresql+asyncpg://user:password@localhost:5432/dbname"
    REDIS_URL: str = "redis://localhost:6379"

    # --- JWT Authentication ---
    JWT_SECRET: str = "super_secret_key_change_me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_SECONDS: int = 3600 # 1 hour

    # --- Email Service (SMTP) ---
    MAIL_USERNAME: EmailStr = "example@smtp.com"
    MAIL_PASSWORD: str = "app_password"
    MAIL_FROM: EmailStr = "noreply@example.com"
    MAIL_PORT: int = 465
    MAIL_SERVER: str = "smtp.example.com"
    MAIL_FROM_NAME: str = "RestApp Support"
    MAIL_STARTTLS: bool = False
    MAIL_SSL_TLS: bool = True
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    # --- Cloudinary Upload Service ---
    CLD_NAME: str = "your_cloud_name"
    CLD_API_KEY: int = 123456789012345
    CLD_API_SECRET: str = "your_api_secret_change_me"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

config = Settings()

def get_settings() -> Settings:
    """
    Returns the singleton instance of the application settings.

    This function can be used as a FastAPI dependency for accessing configuration.

    :return: The application settings object.
    :rtype: :class:`Settings`
    """
    return config