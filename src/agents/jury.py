"""Jury agents: each votes Faithful or Mutated based on claim, truth, and FactFrame."""

from langchain_openai import ChatOpenAI

from schemas import FactFrame, JuryOutput
from prompts import load_jury_template, load_role_instruction

def _create_jury(config: dict) -> ChatOpenAI:
    """Create a jury agent with structured output (JuryOutput)."""
    model_name = config.get("models", {}).get("agents", "gpt-4o-mini")
    llm = ChatOpenAI(model=model_name)
    return llm.with_structured_output(JuryOutput)


def run_jury(
    agent_name: str,
    claim: str,
    truth: str,
    fact_frame: FactFrame,
    config: dict,
    *,
    transcript: list[dict] | None = None,
) -> JuryOutput:
    """Run a jury agent on a (claim, truth) pair and FactFrame. Optional debate transcript for revote."""
    template = load_jury_template("vote_template")
    role_instruction = load_role_instruction(agent_name)
    fact_frame_str = fact_frame.model_dump_json(indent=2)

    debate_section = ""
    if transcript:
        lines = [
            f"{t.get('speaker', 'Agent')}: {t.get('content', '')}"
            for t in transcript
        ]
        debate_section = "\n\nDEBATE TRANSCRIPT:\n" + "\n".join(lines) + "\n\nConsider the arguments above before voting.\n\n---\n"

    prompt = template.format(
        role_instruction=role_instruction.strip(),
        claim=claim,
        truth=truth,
        fact_frame=fact_frame_str,
        debate_section=debate_section,
    )
    jury = _create_jury(config)
    return jury.invoke(prompt)