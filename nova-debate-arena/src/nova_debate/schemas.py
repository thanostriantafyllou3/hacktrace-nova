from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


VerdictLabel = Literal["FAITHFUL", "PARTIALLY_FAITHFUL", "MUTATED"]


class DebateTurn(BaseModel):
    agent: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JudgeVerdict(BaseModel):
    verdict: VerdictLabel = Field(..., description="Final label")
    confidence: float = Field(..., ge=0.0, le=1.0)
    one_sentence_summary: str
    rationale: List[str]
    critical_differences: List[str] = Field(default_factory=list)
    what_would_make_it_faithful: List[str] = Field(default_factory=list)


class DebateResult(BaseModel):
    row_id: int
    claim: str
    truth: str
    turns: List[DebateTurn]
    verdict: Optional[JudgeVerdict] = None
