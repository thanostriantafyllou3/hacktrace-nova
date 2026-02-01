from pydantic import BaseModel, Field
from typing import Optional


class Fact(BaseModel):
    """An extracted fact with claim vs truth. Category is free-form."""
    category: str = Field(
        description="Type of fact extracted",
    )
    claim_says: Optional[str] = Field(
        default=None,
        description="What the claim states for this fact",
    )
    truth_says: Optional[str] = Field(
        default=None,
        description="What the truth states for this fact",
    )
    note: Optional[str] = Field(
        default=None,
        description="Brief note, e.g. 'mismatch', 'omitted in claim', 'added in claim', 'not supported by truth', etc.",
    )


class FactFrame(BaseModel):
    """Structured extraction of key facts from (claim, truth) pairs to ground debate."""
    facts: list[Fact] = Field(
        default_factory=list,
        description="Key facts extracted and compared. Each has category, claim_says, truth_says, and optional note.",
    )
