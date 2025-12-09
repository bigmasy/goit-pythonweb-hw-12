from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from collections.abc import Sequence

from src.database.models import User
from src.schemas import UserCreate

class UserRepository:
    """
    Repository class for managing all database operations related to the User model.

    :param session: The asynchronous database session.
    :type session: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    """
    def __init__(self, session: AsyncSession):
        self.db = session

    async def get_all(self) -> Sequence[User]:
        """
        Retrieves all user records from the database.

        :return: A sequence of User objects.
        :rtype: :class:`collections.abc.Sequence`[:class:`src.database.models.User`]
        """
        query = select(User)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_user_by_id(self, user_id: int) -> User | None:
        """
        Retrieves a single user by their unique ID.

        :param user_id: The ID of the user to retrieve.
        :type user_id: int
        :return: The User object if found, otherwise None.
        :rtype: :class:`src.database.models.User` | None
        """
        stmt = select(User).filter_by(id=user_id)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        """
        Retrieves a single user by their unique username.

        :param username: The username of the user to retrieve.
        :type username: str
        :return: The User object if found, otherwise None.
        :rtype: :class:`src.database.models.User` | None
        """
        stmt = select(User).filter_by(username=username)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """
        Retrieves a single user by their unique email address.

        :param email: The email address of the user to retrieve.
        :type email: str
        :return: The User object if found, otherwise None.
        :rtype: :class:`src.database.models.User` | None
        """
        stmt = select(User).filter_by(email=email)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def create_user(self, body: UserCreate, avatar: str = None) -> User:
        """
        Creates a new user record in the database.

        The password field from the Pydantic schema is expected to contain the 
        hashed password before calling this method.

        :param body: The user creation data.
        :type body: :class:`src.schemas.UserCreate`
        :param avatar: Optional URL for the user's avatar. Defaults to None.
        :type avatar: str | None
        :return: The newly created User object.
        :rtype: :class:`src.database.models.User`
        """
        user = User(
            **body.model_dump(exclude_unset=True, exclude={"password"}),
            hashed_password=body.password,
            avatar=avatar
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def confirmed_email(self, email: str) -> None:
        """
        Updates the confirmation status of a user's email to True.

        :param email: The email address of the user to confirm.
        :type email: str
        :raises AttributeError: If the user is not found by email.
        :return: None
        :rtype: None
        """
        user = await self.get_user_by_email(email)
        user.confirmed = True
        await self.db.commit()

    async def update_avatar_url(self, email: str, url: str) -> User:
        """
        Updates the avatar URL for a user identified by their email.

        :param email: The email address of the user.
        :type email: str
        :param url: The new avatar URL.
        :type url: str
        :raises AttributeError: If the user is not found by email.
        :return: The updated User object.
        :rtype: :class:`src.database.models.User`
        """
        user = await self.get_user_by_email(email)
        user.avatar = url
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def set_new_password(self, email: str, new_password_hash: str) -> User:
        """
        Updates the hashed password for a user identified by their email.

        :param email: The email address of the user.
        :type email: str
        :param new_password_hash: The new hashed password string.
        :type new_password_hash: str
        :raises AttributeError: If the user is not found by email.
        :return: The updated User object.
        :rtype: :class:`src.database.models.User`
        """
        user = await self.get_user_by_email(email)
        user.hashed_password = new_password_hash
        await self.db.commit()
        await self.db.refresh(user)
        return user