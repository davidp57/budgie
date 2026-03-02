"""Pydantic schemas for User model."""

import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Schema for creating a new user.

    Attributes:
        username: Unique username, 3-50 characters.
        password: Plain text password, minimum 8 characters.
    """

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class UserRead(BaseModel):
    """Schema for reading user data (response).

    Attributes:
        id: User ID.
        username: Username.
        created_at: Account creation timestamp.
    """

    model_config = {"from_attributes": True}

    id: int
    username: str
    created_at: datetime.datetime
