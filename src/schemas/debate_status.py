"""Schema for debate termination checks."""

from pydantic import BaseModel, Field


class DebateStatus(BaseModel):
    """Result of checking whether the debate should stop early."""

    conceded: bool = Field(
        description="True if either side has explicitly conceded or changed their position to agree with the other side.",
    )
    no_new_arguments: bool = Field(
        description="True if the last exchange introduced no new substantive arguments—sides are restating or have reached a stalemate.",
    )
