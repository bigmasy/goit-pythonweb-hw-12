from typing import List

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db

from src.schemas import ContactCreate, ContactResponse, ContactUpdate
from src.services.contacts import ContactService, DuplicateContactError

from src.services.auth import get_current_user
from src.database.models import User

router = APIRouter(prefix='/contacts', tags=['contacts'])


@router.get("/search", response_model=List[ContactResponse])
async def search_contacts(
    query: str = Query(min_length=3, description="Search string by first name, last name, or email."),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Searches contacts belonging to the current user by matching a query string
    against the first name, last name, or email.

    :param query: The search string (min length 3).
    :type query: str
    :param skip: The number of contacts to skip (for pagination). Defaults to 0.
    :type skip: int
    :param limit: The maximum number of contacts to return. Defaults to 100.
    :type limit: int
    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :param user: The authenticated user who owns the contacts.
    :type user: :class:`src.database.models.User`
    :return: A list of matching contacts.
    :rtype: List[:class:`src.schemas.ContactResponse`]
    """
    contact_service = ContactService(db)
    return await contact_service.search_contacts(query=query, skip=skip, limit=limit, user=user)


@router.get('/birthdays', response_model=List[ContactResponse])
async def get_upcoming_birthdays(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Retrieves a list of contacts belonging to the current user whose birthdays
    are upcoming within the next 7 days.

    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :param user: The authenticated user who owns the contacts.
    :type user: :class:`src.database.models.User`
    :return: A list of contacts with upcoming birthdays.
    :rtype: List[:class:`src.schemas.ContactResponse`]
    """
    contact_service = ContactService(db)
    return await contact_service.get_upcoming_birthdays(user=user)


@router.get('/', response_model=List[ContactResponse])
async def read_contacts(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Retrieves a list of contacts belonging to the current user with pagination.

    :param skip: The number of contacts to skip (for pagination). Defaults to 0.
    :type skip: int
    :param limit: The maximum number of contacts to return. Defaults to 100.
    :type limit: int
    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :param user: The authenticated user who owns the contacts.
    :type user: :class:`src.database.models.User`
    :return: A list of contacts.
    :rtype: List[:class:`src.schemas.ContactResponse`]
    """
    contact_service = ContactService(db)
    contacts = await contact_service.get_contacts(skip=skip, limit=limit, user=user)
    return contacts


@router.get('/{contact_id}', response_model=ContactResponse)
async def read_contact_by_id(contact_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Retrieves a single contact by its unique ID, ensuring it belongs to the current user.

    :param contact_id: The ID of the contact to retrieve.
    :type contact_id: int
    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :param user: The authenticated user who owns the contacts.
    :type user: :class:`src.database.models.User`
    :raises HTTPException: 404 Not Found if the contact does not exist or does not belong to the user.
    :return: The requested contact object.
    :rtype: :class:`src.schemas.ContactResponse`
    """
    contact_service = ContactService(db)
    contact = await contact_service.get_contact_by_id(contact_id, user=user)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


@router.post('/', response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(body: ContactCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Creates a new contact for the current user.

    :param body: The data for the new contact.
    :type body: :class:`src.schemas.ContactCreate`
    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :param user: The authenticated user who is creating the contact.
    :type user: :class:`src.database.models.User`
    :raises HTTPException: 409 Conflict if a contact with the same unique identifier (e.g., email) already exists for the user.
    :return: The newly created contact object.
    :rtype: :class:`src.schemas.ContactResponse`
    """
    contact_service = ContactService(db)
    try:
        return await contact_service.create_contact(body, user=user)
    except DuplicateContactError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.put('/{contact_id}', response_model=ContactResponse)
async def update_contact(body: ContactUpdate, contact_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Updates an existing contact by ID, ensuring it belongs to the current user.

    :param body: The update data for the contact.
    :type body: :class:`src.schemas.ContactUpdate`
    :param contact_id: The ID of the contact to update.
    :type contact_id: int
    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :param user: The authenticated user who owns the contact.
    :type user: :class:`src.database.models.User`
    :raises HTTPException: 404 Not Found if the contact does not exist or does not belong to the user.
    :raises HTTPException: 409 Conflict if the update results in a duplicate unique identifier (e.g., email) for the user.
    :return: The updated contact object.
    :rtype: :class:`src.schemas.ContactResponse`
    """
    contact_service = ContactService(db)
    try:
        contact = await contact_service.update_contact(body=body, contact_id=contact_id, user=user)
    except DuplicateContactError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)

    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    return contact


@router.delete('/{contact_id}', response_model=ContactResponse)
async def remove_contact(contact_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Deletes a contact by ID, ensuring it belongs to the current user.

    :param contact_id: The ID of the contact to delete.
    :type contact_id: int
    :param db: The asynchronous database session dependency.
    :type db: :class:`sqlalchemy.ext.asyncio.AsyncSession`
    :param user: The authenticated user who owns the contact.
    :type user: :class:`src.database.models.User`
    :raises HTTPException: 404 Not Found if the contact does not exist or does not belong to the user.
    :return: The deleted contact object.
    :rtype: :class:`src.schemas.ContactResponse`
    """
    contact_service = ContactService(db)
    result = await contact_service.remove_contact(contact_id, user=user)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result