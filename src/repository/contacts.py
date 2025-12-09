from typing import List
from datetime import date, timedelta

from sqlalchemy import select, or_, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.schemas import ContactUpdate, ContactCreate

from sqlalchemy.exc import IntegrityError

class DuplicateContactError(Exception):
    """Custom exception raised when attempting to create or update a contact
    with a duplicate unique identifier (email or phone number) for a given user.
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class ContactRepository:
    """
    Repository class for managing all database operations related to the Contact model.

    :param session: The asynchronous database session.
    :type session: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    """
    def __init__(self, session: AsyncSession):
        self.db = session

    async def get_contacts(self, skip: int, limit: int, user: User) -> List[Contact]:
        """
        Retrieves a paginated list of contacts belonging to a specific user.

        :param skip: The number of records to skip.
        :type skip: int
        :param limit: The maximum number of records to return.
        :type limit: int
        :param user: The owner of the contacts.
        :type user: :class:`src.database.models.User`
        :return: A list of Contact objects.
        :rtype: List[:class:`src.database.models.Contact`]
        """
        stmt = select(Contact).filter_by(user_id = user.id).offset(skip).limit(limit)
        contacts = await self.db.execute(stmt)
        return list(contacts.scalars().all())

    async def get_contact_by_id(self, contact_id: int, user: User) -> Contact | None:
        """
        Retrieves a single contact by its ID, restricted to the specified user.

        :param contact_id: The ID of the contact to retrieve.
        :type contact_id: int
        :param user: The owner of the contact.
        :type user: :class:`src.database.models.User`
        :return: The Contact object if found, otherwise None.
        :rtype: :class:`src.database.models.Contact` | None
        """
        stmt = select(Contact).filter_by(id = contact_id, user_id = user.id)
        contact = await self.db.execute(stmt)
        return contact.scalar_one_or_none()

    async def create_contact(self, body: ContactCreate, user: User) -> Contact:
        """
        Creates a new contact record for the specified user.

        Handles unique constraints for email and phone number per user.

        :param body: The data for creating the new contact.
        :type body: :class:`src.schemas.ContactCreate`
        :param user: The user who owns the new contact.
        :type user: :class:`src.database.models.User`
        :raises DuplicateContactError: If a contact with the same email or phone number already exists for the user.
        :raises IntegrityError: For other unexpected database integrity errors.
        :return: The newly created Contact object.
        :rtype: :class:`src.database.models.Contact`
        """
        contact = Contact(**body.model_dump(), user_id = user.id)
        self.db.add(contact)
        try:
            await self.db.commit()
            await self.db.refresh(contact)
            return contact
        except IntegrityError as e:
            await self.db.rollback()
            error_message = str(e.orig)
            if 'duplicate key value violates unique constraint' in error_message:
                if 'uq_contact_email_user' in error_message:  # Use the constraint name from models.py
                    raise DuplicateContactError("Contact with this email already exists.")
                if 'uq_contact_phone_user' in error_message:  # Use the constraint name from models.py
                    raise DuplicateContactError("Contact with this phone number already exists.")
            raise e

    async def update_contact(self, contact_id: int, body: ContactUpdate, user: User) -> Contact | None:
        """
        Updates an existing contact record by ID, restricted to the specified user.

        Handles unique constraints for email and phone number per user during update.

        :param contact_id: The ID of the contact to update.
        :type contact_id: int
        :param body: The data containing fields to update.
        :type body: :class:`src.schemas.ContactUpdate`
        :param user: The owner of the contact.
        :type user: :class:`src.database.models.User`
        :raises DuplicateContactError: If the update results in a duplicate email or phone number for the user.
        :raises IntegrityError: For other unexpected database integrity errors.
        :return: The updated Contact object if found and updated, otherwise None.
        :rtype: :class:`src.database.models.Contact` | None
        """
        contact = await self.get_contact_by_id(contact_id = contact_id, user = user)
        if contact:
            update_data = body.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(contact, key, value)
            try:
                await self.db.commit()
                await self.db.refresh(contact)
            except IntegrityError as e:
                await self.db.rollback()
                error_message = str(e.orig)
                if 'duplicate key value violates unique constraint' in error_message:
                    # Note: Constraint check needs to be precise based on your database setup
                    if 'uq_contact_email_user' in error_message:
                        raise DuplicateContactError("Contact with this email already exists.")
                    if 'uq_contact_phone_user' in error_message:
                        raise DuplicateContactError("Contact with this phone number already exists.")
                raise e

        return contact

    async def remove_contact(self, contact_id: int, user: User) -> Contact | None:
        """
        Deletes a contact record by ID, restricted to the specified user.

        :param contact_id: The ID of the contact to delete.
        :type contact_id: int
        :param user: The owner of the contact.
        :type user: :class:`src.database.models.User`
        :return: The deleted Contact object if found and deleted, otherwise None.
        :rtype: :class:`src.database.models.Contact` | None
        """
        contact = await self.get_contact_by_id(contact_id = contact_id, user = user)
        if contact:
            await self.db.delete(contact)
            await self.db.commit()
        return contact

    async def search_contacts(self, query: str, skip: int, limit: int, user: User) -> List[Contact]:
        """
        Searches contacts belonging to the user by partial match (case-insensitive)
        on first name, last name, or email.

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
        stmt = select(Contact).filter_by(user_id = user.id).filter(or_(
                Contact.first_name.ilike(f"%{query}%"),
                Contact.last_name.ilike(f"%{query}%"),
                Contact.email.ilike(f"%{query}%")
            )).offset(skip).limit(limit)
        contacts = await self.db.execute(stmt)
        return list(contacts.scalars().all())


    async def get_upcoming_birthdays(self, user: User) -> List[Contact]:
        """
        Retrieves contacts whose birthdays fall within the next 7 days from today.

        The search is performed by comparing the month and day of the birthday
        regardless of the year.

        :param user: The owner of the contacts.
        :type user: :class:`src.database.models.User`
        :return: A list of Contact objects with upcoming birthdays.
        :rtype: List[:class:`src.database.models.Contact`]
        """
        today = date.today()
        end_date = today + timedelta(days=7)

        today_str = today.strftime('%m-%d')
        end_date_str = end_date.strftime('%m-%d')

        stmt = select(Contact).filter_by(user_id = user.id)

        # Logic to handle date ranges that cross the year boundary (e.g., Dec 28 - Jan 4)
        if today.year == end_date.year:
            # Simple case: range within the same year
            stmt = stmt.filter(
                func.to_char(Contact.birthday, 'MM-DD').between(today_str, end_date_str)
            )
        else:
            # Cross-year case: check from today to Dec 31 OR from Jan 1 to end_date
            stmt = stmt.filter(
                or_(
                    func.to_char(Contact.birthday, 'MM-DD') >= today_str,
                    func.to_char(Contact.birthday, 'MM-DD') <= end_date_str
                )
            )

        contacts = await self.db.execute(stmt)
        return list(contacts.scalars().all())