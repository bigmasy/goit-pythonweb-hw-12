from sqlalchemy.ext.asyncio import AsyncSession


from src.repository.contacts import ContactRepository, DuplicateContactError
from src.database.models import User
from src.schemas import ContactUpdate, ContactCreate

class ContactService:
    """
    Service layer for contact-related operations.

    This service acts as an intermediary, handling business logic (if any)
    and exception propagation between the API router and the data repository.

    :param db: The asynchronous database session.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    """
    def __init__(self, db: AsyncSession):
        self.contact_repository = ContactRepository(db)

    async def get_contacts(self, skip: int, limit: int, user: User):
        """
        Retrieves a paginated list of contacts for the given user.

        :param skip: The number of records to skip (offset).
        :type skip: int
        :param limit: The maximum number of records to return.
        :type limit: int
        :param user: The owner of the contacts.
        :type user: :class:`src.database.models.User`
        :return: A list of Contact objects.
        :rtype: List[:class:`src.database.models.Contact`]
        """
        return await self.contact_repository.get_contacts(skip=skip, limit=limit, user=user)

    async def get_contact_by_id(self, contact_id: int, user: User):
        """
        Retrieves a single contact by ID, scoped to the specified user.

        :param contact_id: The ID of the contact to retrieve.
        :type contact_id: int
        :param user: The owner of the contact.
        :type user: :class:`src.database.models.User`
        :return: The Contact object if found, otherwise None.
        :rtype: :class:`src.database.models.Contact` | None
        """
        return await self.contact_repository.get_contact_by_id(contact_id=contact_id, user=user)

    async def create_contact(self, body: ContactCreate, user: User):
        """
        Creates a new contact for the user.

        Propagates :exc:`src.repository.contacts.DuplicateContactError` if a unique constraint is violated.

        :param body: The data for creating the new contact.
        :type body: :class:`src.schemas.ContactCreate`
        :param user: The user who owns the new contact.
        :type user: :class:`src.database.models.User`
        :raises DuplicateContactError: If a contact with the same unique data already exists.
        :return: The newly created Contact object.
        :rtype: :class:`src.database.models.Contact`
        """
        try:
            return await self.contact_repository.create_contact(body=body, user=user)
        except DuplicateContactError as e:
            raise e

    async def update_contact(self, contact_id: int, body: ContactUpdate, user: User):
        """
        Updates an existing contact by ID.

        Propagates :exc:`src.repository.contacts.DuplicateContactError` if a unique constraint is violated.

        :param contact_id: The ID of the contact to update.
        :type contact_id: int
        :param body: The data containing fields to update.
        :type body: :class:`src.schemas.ContactUpdate`
        :param user: The owner of the contact.
        :type user: :class:`src.database.models.User`
        :raises DuplicateContactError: If the update results in a unique constraint violation.
        :return: The updated Contact object if found, otherwise None.
        :rtype: :class:`src.database.models.Contact` | None
        """
        try:
            return await self.contact_repository.update_contact(contact_id=contact_id, body=body, user=user)
        except DuplicateContactError as e:
            raise e

    async def remove_contact(self, contact_id: int, user: User):
        """
        Deletes a contact by ID, scoped to the specified user.

        :param contact_id: The ID of the contact to delete.
        :type contact_id: int
        :param user: The owner of the contact.
        :type user: :class:`src.database.models.User`
        :return: The deleted Contact object if found and deleted, otherwise None.
        :rtype: :class:`src.database.models.Contact` | None
        """
        return await self.contact_repository.remove_contact(contact_id=contact_id, user=user)

    async def search_contacts(self, query: str, skip: int, limit: int, user: User):
        """
        Searches contacts by matching the query against first name, last name, or email.

        :param query: The search string.
        :type query: str
        :param skip: The number of records to skip.
        :type skip: int
        :param limit: The maximum number of records to return.
        :type limit: int
        :param user: The owner of the contacts.
        :type user: :class:`src.database.models.User`
        :return: A list of matching Contact objects.
        :rtype: List[:class:`src.database.models.Contact`]
        """
        return await self.contact_repository.search_contacts(query=query, skip=skip, limit=limit, user=user)

    async def get_upcoming_birthdays(self, user: User):
        """
        Retrieves contacts whose birthdays fall within the next 7 days.

        :param user: The owner of the contacts.
        :type user: :class:`src.database.models.User`
        :return: A list of Contact objects with upcoming birthdays.
        :rtype: List[:class:`src.database.models.Contact`]
        """
        return await self.contact_repository.get_upcoming_birthdays(user=user)