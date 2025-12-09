from datetime import date, datetime
from sqlalchemy import Integer, String, Date, Boolean, ForeignKey, DateTime, func, UniqueConstraint, MetaData, Column
from sqlalchemy.orm import mapped_column, Mapped, DeclarativeBase, relationship
from enum import Enum

class Base(DeclarativeBase):
    """
    Base class for declarative class definitions.
    All ORM models in the application should inherit from this class.
    """
    pass

metadata_ = MetaData()


class MinimalBase(DeclarativeBase):
    """
    Abstract base class providing common metadata settings.
    """
    __abstract__ = True
    metadata = metadata_


class IdOrmModel(MinimalBase):
    """
    Abstract base class providing a standard 'id' primary key column.
    """
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)

class UserRole(str, Enum):
    """
    Enumeration for user roles within the application.
    """
    USER = 'user'
    ADMIN = 'admin'


class User(Base):
    """
    SQLAlchemy ORM model representing the 'users' table.

    Users are the owners of contacts and have authentication-related fields.

    :ivar id: Primary key integer.
    :vartype id: int
    :ivar username: Unique username (String, max 20).
    :vartype username: str
    :ivar email: Unique email address (String, max 50).
    :vartype email: str
    :ivar hashed_password: Hashed password string.
    :vartype hashed_password: str
    :ivar confirmed: Boolean indicating if the user's email is confirmed (default False).
    :vartype confirmed: bool
    :ivar avatar: URL to the user's avatar image (nullable String, max 255).
    :vartype avatar: str | None
    :ivar refresh_token: JWT refresh token for session management (nullable String, max 255).
    :vartype refresh_token: str | None
    :ivar contacts: List of contacts associated with this user (One-to-Many relationship).
    :vartype contacts: list['Contact']
    :ivar created_at: Timestamp of user creation (DateTime, defaults to current time).
    :vartype created_at: datetime
    :ivar role: User's role (defaults to UserRole.USER).
    :vartype role: :class:`UserRole`
    """
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    email : Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255),nullable=False)
    confirmed : Mapped[bool] = mapped_column(Boolean, default=False)
    avatar: Mapped[str|None] = mapped_column(String(255))
    refresh_token: Mapped[str|None] = mapped_column(String(255))
    contacts: Mapped[list['Contact']] = relationship(back_populates='user')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    role: Mapped[UserRole] = mapped_column(String, default = UserRole.USER)


class Contact(Base):
    """
    SQLAlchemy ORM model representing the 'contacts' table.

    Stores contact information associated with a specific user.

    :ivar id: Primary key integer.
    :vartype id: int
    :ivar first_name: Contact's first name (String, max 20).
    :vartype first_name: str
    :ivar last_name: Contact's last name (nullable String, max 20).
    :vartype last_name: str | None
    :ivar email: Contact's email address (String, max 50). Unique per user.
    :vartype email: str
    :ivar phone_number: Contact's phone number (String, max 15). Unique per user.
    :vartype phone_number: str
    :ivar birthday: Contact's date of birth.
    :vartype birthday: :class:`datetime.date`
    :ivar additional_data: Additional notes or data about the contact (nullable String, max 50).
    :vartype additional_data: str | None
    :ivar user_id: Foreign key linking to the owner user's ID. Deletes cascade.
    :vartype user_id: int
    :ivar user: Relationship object linking to the owner user (Many-to-One relationship).
    :vartype user: :class:`User`
    """
    __tablename__ = 'contacts'
    __table_args__=(
        UniqueConstraint('email', 'user_id', name='uq_contact_email_user'),
        UniqueConstraint('phone_number', 'user_id', name='uq_contact_phone_user')
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    last_name: Mapped[str|None] = mapped_column(String(20) ,index=True)
    email: Mapped[str] = mapped_column(String(50),nullable=False, index=True)
    phone_number: Mapped[str] = mapped_column(String(15), nullable=False)
    birthday: Mapped[date] = mapped_column(Date)
    additional_data: Mapped[str|None] = mapped_column(String(50))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    user: Mapped["User"] = relationship(back_populates='contacts')