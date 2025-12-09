from sqlalchemy.ext.asyncio import AsyncSession
from libgravatar import Gravatar

from src.repository.users import UserRepository
from src.schemas import UserCreate

class UserService:
    """
    Service layer for user-related operations.

    Handles business logic such as generating default avatars (Gravatar) and
    delegating CRUD operations to the UserRepository.

    :param db: The asynchronous database session.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    """
    def __init__(self, db: AsyncSession):
        self.repository = UserRepository(db)

    async def create_user(self, body: UserCreate):
        """
        Creates a new user record.

        Before creation, it attempts to generate a default avatar URL using Gravatar
        based on the user's email.

        :param body: The user creation data.
        :type body: :class:`src.schemas.UserCreate`
        :return: The newly created User object.
        :rtype: :class:`src.database.models.User`
        """
        avatar = None
        try:
            g = Gravatar(body.email)
            avatar = g.get_image()
        except Exception as e:
            print(e)

        return await self.repository.create_user(body, avatar)

    async def get_user_by_id(self, user_id: int):
        """
        Retrieves a user by their unique ID.

        :param user_id: The ID of the user.
        :type user_id: int
        :return: The User object if found, otherwise None.
        :rtype: :class:`src.database.models.User` | None
        """
        return await self.repository.get_user_by_id(user_id)

    async def get_user_by_username(self, username: str):
        """
        Retrieves a user by their unique username.

        :param username: The username of the user.
        :type username: str
        :return: The User object if found, otherwise None.
        :rtype: :class:`src.database.models.User` | None
        """
        return await self.repository.get_user_by_username(username)

    async def get_user_by_email(self, email: str):
        """
        Retrieves a user by their unique email address.

        :param email: The email address of the user.
        :type email: str
        :return: The User object if found, otherwise None.
        :rtype: :class:`src.database.models.User` | None
        """
        return await self.repository.get_user_by_email(email)

    async def confirmed_email(self, email: str):
        """
        Confirms the user's email address in the database.

        :param email: The email address of the user to confirm.
        :type email: str
        :return: The result of the repository operation (None).
        :rtype: None
        """
        return await self.repository.confirmed_email(email)

    async def update_avatar_url(self, email: str, url: str):
        """
        Updates the avatar URL for a user identified by their email.

        :param email: The email address of the user.
        :type email: str
        :param url: The new avatar URL.
        :type url: str
        :return: The updated User object.
        :rtype: :class:`src.database.models.User`
        """
        return await self.repository.update_avatar_url(email, url)

    async def set_new_password(self, email: str, new_password_hash: str):
        """
        Updates the hashed password for a user identified by their email.

        :param email: The email address of the user.
        :type email: str
        :param new_password_hash: The new hashed password string.
        :type new_password_hash: str
        :return: The updated User object.
        :rtype: :class:`src.database.models.User`
        """
        return await self.repository.set_new_password(email, new_password_hash)