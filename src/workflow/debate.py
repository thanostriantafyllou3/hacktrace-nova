"""Debate: when verdict is split, agents argue using the same role instructions and context as votes."""

from langchain_openai import ChatOpenAI

from schemas import FactFrame, JuryOutput
from prompts import load_jury_template, load_role_instruction


def run_debate(
    initial_vote_outputs: list[tuple[str, JuryOutput]],
    claim: str,
    truth: str,
    fact_frame: FactFrame,
    config: dict,
) -> list[dict]:
    """
    Run one round of debate: Mutated side presents, then Faithful side.
    Returns transcript: [{"speaker": str, "content": str}, ...]
    """
    mutated = [(n, o) for n, o in initial_vote_outputs if o.verdict.strip().lower() == "mutated"]
    faithful = [(n, o) for n, o in initial_vote_outputs if o.verdict.strip().lower() == "faithful"]

    if not mutated or not faithful:
        return []

    model_name = config.get("models", {}).get("agents", "gpt-4o-mini")
    llm = ChatOpenAI(model=model_name)
    template = load_jury_template("debate_template")
    fact_frame_str = fact_frame.model_dump_json(indent=2)
    transcript = []

    # Mutated side speaks first (pick first agent)
    speaker, output = mutated[0]
    role_instruction = load_role_instruction(speaker)
    faithful_args = "\n".join(f"{n}: {o.reasoning}" for n, o in faithful[:2])
    prompt = template.format(
        role_instruction=role_instruction.strip(),
        claim=claim,
        truth=truth,
        fact_frame=fact_frame_str,
        verdict="Mutated",
        reasoning=output.reasoning,
        other_side_args=f"Faithful side's reasoning:\n{faithful_args}",
    )
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    transcript.append({"speaker": speaker, "content": content})

    # Faithful side responds
    speaker, output = faithful[0]
    role_instruction = load_role_instruction(speaker)
    mutated_args = "\n".join(f"{n}: {o.reasoning}" for n, o in mutated[:2])
    prompt = template.format(
        role_instruction=role_instruction.strip(),
        claim=claim,
        truth=truth,
        fact_frame=fact_frame_str,
        verdict="Faithful",
        reasoning=output.reasoning,
        other_side_args=f"Mutated side's argument:\n{transcript[0]['content']}\n\nMutated reasoning:\n{mutated_args}",
    )
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    transcript.append({"speaker": speaker, "content": content})

    return transcript
