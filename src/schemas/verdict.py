from pydantic import BaseModel, Field
from typing import Optional


class AxisResult(BaseModel):
    """One rubric axis: did the claim pass? Axis name comes from config (e.g. numeric_fidelity). Note is optional."""
    axis: str = Field(
        description="Axis name from config (e.g. numeric_fidelity, scope_fidelity)"
    )
    passed: bool = Field(
        description="Yes if claim passes this axis, No otherwise"
    )
    note: Optional[str] = Field(
        default=None,
        description="Explanation of why the claim passed or failed this axis",
    )


class Verdict(BaseModel):
    """Final verdict from the Foreperson after applying the rubric."""
    verdict: str = Field(
        description="Faithful, Mutated, or Ambiguous",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the verdict, 0.0 to 1.0",
    )
    axis_results: list[AxisResult] = Field(
        default_factory=list,
        description="One entry per rubric axis from config.",
    )
    summary: str = Field(
        description="Summary of the verdict and the reasons for it",
    )
    minimal_edit: Optional[str] = Field(
        default=None,
        description="Minimal edit that would make the claim faithful (if Mutated)",
    )
    dissent_note: Optional[str] = Field(
        default=None,
        description="Note if significant dissent from jury (2+ agents on minority verdict)",
    )
