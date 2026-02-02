"""Debate: when verdict is split, agents argue until max rounds, unanimity, or no new arguments."""

from langchain_openai import ChatOpenAI

from schemas import FactFrame, JuryOutput, DebateStatus
from prompts import load_jury_template, load_role_instruction, load


def run_debate_round(
    initial_vote_outputs: list[tuple[str, JuryOutput]],
    claim: str,
    truth: str,
    fact_frame: FactFrame,
    config: dict,
    transcript: list[dict],
    round_idx: int,
) -> dict:
    """
    Run one debate round: Mutated speaks, then Faithful speaks.
    Returns update dict: {transcript, debate_status, debate_round_idx}.
    """
    mutated = [(n, o) for n, o in initial_vote_outputs if o.verdict.strip().lower() == "mutated"]
    faithful = [(n, o) for n, o in initial_vote_outputs if o.verdict.strip().lower() == "faithful"]

    if not mutated or not faithful:
        max_rounds = config.get("debate", {}).get("max_rounds", 2)
        return {"transcript": [], "debate_status": None, "debate_round_idx": max_rounds}

    debate_config = config.get("debate", {})
    max_rounds = debate_config.get("max_rounds", 2)
    components = config.get("components", {})
    jury_cfg = components.get("agents", {})
    status_cfg = components.get("debate_status", {})
    jury_model_name = jury_cfg.get("model", "gpt-4.1-mini")
    status_model_name = status_cfg.get("model", "gpt-4.1-mini")
    jury_temp = jury_cfg.get("temperature", 0.2)
    status_temp = status_cfg.get("temperature", 0.2)
    jury_llm = ChatOpenAI(model=jury_model_name, temperature=jury_temp)
    debate_template = load_jury_template("debate_template")
    fact_frame_str = fact_frame.model_dump_json(indent=2)
    mutated_args = "\n".join(f"{n}: {o.reasoning}" for n, o in mutated)
    faithful_args = "\n".join(f"{n}: {o.reasoning}" for n, o in faithful)

    transcript = list(transcript)  # copy

    # Mutated side speaks
    speaker, output = mutated[round_idx % len(mutated)]
    role_instruction = load_role_instruction(speaker)
    if round_idx == 0:
        debate_context = f"Faithful side's initial reasoning:\n{faithful_args}"
        round_instruction = ""
    else:
        debate_context = _format_transcript(transcript)
        round_instruction = "Focus on the most recent exchange."
    prompt = debate_template.format(
        role_instruction=role_instruction.strip(),
        claim=claim,
        truth=truth,
        fact_frame=fact_frame_str,
        verdict="Mutated",
        reasoning=output.reasoning,
        debate_context=debate_context,
        round_instruction=round_instruction,
    )
    response = jury_llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    transcript.append({"speaker": speaker, "content": content, "side": output.verdict})

    # Faithful side speaks
    speaker, output = faithful[round_idx % len(faithful)]
    role_instruction = load_role_instruction(speaker)
    if round_idx == 0:
        debate_context = f"Mutated side's argument:\n{transcript[0]['content']}\n\nMutated reasoning:\n{mutated_args}"
        round_instruction = ""
    else:
        debate_context = _format_transcript(transcript)
        round_instruction = "Focus on the most recent exchange."
    prompt = debate_template.format(
        role_instruction=role_instruction.strip(),
        claim=claim,
        truth=truth,
        fact_frame=fact_frame_str,
        verdict="Faithful",
        reasoning=output.reasoning,
        debate_context=debate_context,
        round_instruction=round_instruction,
    )
    response = jury_llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    transcript.append({"speaker": speaker, "content": content, "side": output.verdict})

    # Check concession or no new arguments
    status_llm = ChatOpenAI(model=status_model_name, temperature=status_temp)
    status_template = load("debate_status_check.txt")
    status = _check_debate_status(transcript, status_template, status_llm)

    return {
        "transcript": transcript,
        "debate_status": status,
        "debate_round_idx": round_idx + 1,
    }


def _format_transcript(transcript: list[dict]) -> str:
    lines = [f"{t['speaker']} ({t.get('side', '?')}): {t['content']}" for t in transcript]
    return "Debate so far:\n" + "\n\n".join(lines)


def _check_debate_status(
    transcript: list[dict],
    prompt_template: str,
    llm: ChatOpenAI,
) -> str | None:
    """Check if debate should stop: conceded or no new arguments."""
    if len(transcript) < 2: 
        return None
    formatted = _format_transcript(transcript)
    prompt = prompt_template.format(transcript=formatted)
    checker = llm.with_structured_output(DebateStatus)
    status = checker.invoke(prompt)
    if status.conceded:
        return "Conceded"
    elif status.no_new_arguments:
        return "No new arguments"
    return "No decision. Debate continues..."
