"""SQLAlchemy ORM models for Budgie.

All models are imported here so that Base.metadata contains
the complete schema when creating tables or generating migrations.
"""

from budgie.models.account import Account
from budgie.models.budget import BudgetAllocation
from budgie.models.category import Category, CategoryGroup
from budgie.models.category_rule import CategoryRule
from budgie.models.envelope import Envelope, envelope_categories
from budgie.models.payee import Payee
from budgie.models.transaction import SplitTransaction, Transaction
from budgie.models.user import User
from budgie.models.webauthn import WebAuthnCredential

__all__ = [
    "Account",
    "BudgetAllocation",
    "Category",
    "CategoryGroup",
    "CategoryRule",
    "Envelope",
    "Payee",
    "SplitTransaction",
    "Transaction",
    "User",
    "WebAuthnCredential",
    "envelope_categories",
]
