from pydantic import BaseModel, Field

from .fact_frame import Fact


class Evidence(BaseModel):
    """One piece of evidence supporting the agent's verdict."""
    fact: Fact = Field(
        description="The fact that is evidence for the verdict"
    )
    issue: str = Field(
        description="Brief description of the mismatch or concern"
    )


class JuryOutput(BaseModel):
    """Output from each jury agent after Round 0 or Round 2."""
    verdict: str = Field(
        description="Faithful or Mutated",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the verdict, 0.0 to 1.0",
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="Evidence supporting the verdict. Empty if Faithful with no concerns.",
    )
    reasoning: str = Field(
        description="Free-form explanation of the verdict",
    )
