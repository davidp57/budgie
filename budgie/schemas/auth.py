"""Pydantic schemas for authentication (login, token response)."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Schema for user login request.

    Attributes:
        username: User's username.
        password: Plain text password.
    """

    username: str
    password: str


class TokenResponse(BaseModel):
    """Schema for JWT token response.

    Attributes:
        access_token: JWT access token string.
        token_type: Always 'bearer'.
    """

    access_token: str
    token_type: str = "bearer"
