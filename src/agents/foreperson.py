"""Foreperson agent: applies rubric to produce final Verdict."""

from langchain_openai import ChatOpenAI

from schemas import Verdict
from prompts import load


def run_foreperson(
    claim: str,
    truth: str,
    fact_frame_str: str,
    transcript_str: str,
    revote_outputs_str: str,
    rubric_questions: str,
    config: dict,
) -> Verdict:
    """Run Foreperson to produce final Verdict."""
    model_name = config.get("models", {}).get("foreperson", "gpt-4o-mini")
    llm = ChatOpenAI(model=model_name).with_structured_output(Verdict)

    prompt = load("foreperson.txt").format(
        claim=claim,
        truth=truth,
        fact_frame=fact_frame_str,
        transcript=transcript_str,
        revote_outputs=revote_outputs_str,
        rubric_questions=rubric_questions,
    )
    return llm.invoke(prompt)
