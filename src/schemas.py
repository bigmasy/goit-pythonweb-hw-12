from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from src.database.models import UserRole

class ContactBase(BaseModel):
    """
    Base schema for contact properties shared across creation and representation.

    :ivar first_name: Contact's first name (max 20 chars).
    :vartype first_name: str
    :ivar last_name: Contact's last name (max 20 chars, optional).
    :vartype last_name: str | None
    :ivar email: Contact's email address (max 50 chars).
    :vartype email: :class:`pydantic.EmailStr`
    :ivar phone_number: Contact's phone number (max 15 chars).
    :vartype phone_number: str
    :ivar birthday: Contact's date of birth.
    :vartype birthday: :class:`datetime.date`
    :ivar additional_data: Additional notes (max 50 chars, optional).
    :vartype additional_data: str | None
    """
    first_name: str = Field(max_length=20)
    last_name: str | None = Field(max_length=20)
    email: EmailStr = Field(max_length=50)
    phone_number: str = Field(max_length=15)
    birthday: date
    additional_data: Optional[str] = Field(default=None, max_length=50)

class ContactCreate(ContactBase):
    """
    Schema for creating a new contact. Inherits all required fields from ContactBase.
    """
    pass

class ContactUpdate(BaseModel):
    """
    Schema for updating an existing contact. All fields are optional.

    :ivar first_name: Optional first name update.
    :vartype first_name: str | None
    :ivar last_name: Optional last name update.
    :vartype last_name: str | None
    :ivar email: Optional email update.
    :vartype email: :class:`pydantic.EmailStr` | None
    :ivar phone_number: Optional phone number update.
    :vartype phone_number: str | None
    :ivar birthday: Optional birthday update.
    :vartype birthday: :class:`datetime.date` | None
    :ivar additional_data: Optional additional data update.
    :vartype additional_data: str | None
    """
    first_name: Optional[str] = Field(default=None, max_length=20)
    last_name: Optional[str] = Field(default=None, max_length=20)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(default=None, max_length=15)
    birthday: Optional[date] = None
    additional_data: Optional[str] = Field(default=None, max_length=50)

class ContactResponse(ContactBase):
    """
    Schema for returning a contact, including database-generated fields.

    :ivar id: The unique ID of the contact.
    :vartype id: int
    :ivar user_id: The ID of the contact's owner.
    :vartype user_id: int
    """
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    """
    Schema for returning user information.

    :ivar id: The unique ID of the user.
    :vartype id: int
    :ivar username: The user's username.
    :vartype username: str
    :ivar email: The user's email address.
    :vartype email: :class:`pydantic.EmailStr`
    :ivar avatar: URL to the user's avatar.
    :vartype avatar: str
    :ivar confirmed: Boolean status of email confirmation.
    :vartype confirmed: bool
    :ivar created_at: Timestamp of user creation.
    :vartype created_at: :class:`datetime.datetime`
    :ivar role: The user's role.
    :vartype role: :class:`src.database.models.UserRole`
    """
    id: int
    username: str
    email: EmailStr
    avatar: str
    confirmed: bool
    created_at: datetime
    role: UserRole

    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    """
    Schema for registering a new user.

    :ivar username: The desired username.
    :vartype username: str
    :ivar email: The user's email address.
    :vartype email: :class:`pydantic.EmailStr`
    :ivar password: The user's password (will be hashed by the service layer).
    :vartype password: str
    """
    username: str
    email: EmailStr
    password: str


class TokenSchema(BaseModel):
    """
    Schema for returning authentication tokens.

    :ivar access_token: The JWT access token.
    :vartype access_token: str
    :ivar token_type: The type of token (usually "bearer").
    :vartype token_type: str
    """
    access_token: str
    token_type: str

class RequestEmail(BaseModel):
    """
    Schema for requesting actions based on a user's email (e.g., resend confirmation).

    :ivar email: The target email address.
    :vartype email: :class:`pydantic.EmailStr`
    """
    email: EmailStr

class RequestPasswordReset(BaseModel):
    """
    Schema for requesting a password reset email.

    :ivar email: The email address associated with the account.
    :vartype email: :class:`pydantic.EmailStr`
    """
    email: EmailStr

class PasswordReset(BaseModel):
    """
    Schema for providing a new password during the reset process.

    :ivar new_password: The new password (min 6, max 72 chars).
    :vartype new_password: str
    """
    new_password: str = Field(min_length=6, max_length=72)