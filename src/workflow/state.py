"""Shared state for the jury LangGraph."""

from typing import Optional

from pydantic import BaseModel, Field

from schemas import FactFrame, JuryOutput, Verdict


class JuryState(BaseModel):
    """State passed through the jury pipeline."""

    # Input
    claim: str = Field(description="The claim to be judged.")
    truth: str = Field(description="The reference truth.")
    config: dict = Field(default_factory=dict, description="App configuration.")

    # Parse
    fact_frame: Optional[FactFrame] = Field(default=None, description="Extracted facts from claim vs truth.")

    # Round 0: Initial vote
    initial_vote_outputs: Optional[list[tuple[str, JuryOutput]]] = Field(
        default=None, description="(agent_name, output) from initial independent vote."
    )

    # Round 1: Debate (when verdict split)
    transcript: Optional[list[dict]] = Field(
        default=None, description="Debate transcript: [{\"speaker\": str, \"content\": str}, ...]."
    )
    skipped_debate: Optional[bool] = Field(
        default=None, description="True if debate was skipped (unanimous initial vote)."
    )
    debate_status: Optional[str] = Field(
        default=None, description="After each round: 'Conceded', 'No new arguments', or 'No decision. Debate continues...'."
    )
    debate_round_idx: int = Field(default=0, description="Current debate round index.")

    # Round 2: Revote
    revote_outputs: Optional[list[tuple[str, JuryOutput]]] = Field(
        default=None, description="(agent_name, output) after revote."
    )

    # Final
    verdict: Optional[Verdict] = Field(default=None, description="Foreperson's final verdict.")
