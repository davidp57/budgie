"""Pydantic schemas for User model."""

import datetime
import re

from pydantic import BaseModel, Field, field_validator

# Password must contain at least one lowercase letter, one uppercase letter,
# and one digit.  Minimum length is enforced by Field(min_length=8).
_PASSWORD_RE = re.compile(r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)")


class UserCreate(BaseModel):
    """Schema for creating a new user.

    Attributes:
        username: Unique username, 3-50 characters.
        password: Plain text password — minimum 8 characters, must contain at
            least one lowercase letter, one uppercase letter, and one digit.
    """

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        """Enforce password complexity requirements.

        Args:
            v: Plain text password.

        Returns:
            The validated password.

        Raises:
            ValueError: If the password does not meet complexity requirements.
        """
        if not _PASSWORD_RE.search(v):
            raise ValueError(
                "Password must contain at least one lowercase letter, "
                "one uppercase letter, and one digit."
            )
        return v


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


class UserPreferences(BaseModel):
    """User preferences returned by GET /api/users/me/preferences.

    Attributes:
        budget_mode: Budgeting mode — ``n1`` (N+1, default: income received in
            M-1 feeds current month without creating virtual transactions) or
            ``n`` (prévisionnel: create virtual income transactions for income
            expected in the current month before it arrives).
    """

    model_config = {"from_attributes": True}

    budget_mode: str


class UserPreferencesUpdate(BaseModel):
    """Payload for PUT /api/users/me/preferences.

    Attributes:
        budget_mode: New budgeting mode value — ``n1`` or ``n``.
    """

    budget_mode: str = Field(..., pattern=r"^(n1|n)$")
