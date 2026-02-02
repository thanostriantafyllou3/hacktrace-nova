"""Debate: when verdict is split, agents argue until max rounds, unanimity, or no new arguments."""

from langchain_openai import ChatOpenAI

from schemas import FactFrame, JuryOutput, DebateStatus
from prompts import load_jury_template, load_role_instruction, load


def run_debate(
    initial_vote_outputs: list[tuple[str, JuryOutput]],
    claim: str,
    truth: str,
    fact_frame: FactFrame,
    config: dict,
) -> list[dict]:
    """
    Run multi-round debate: Mutated and Faithful alternate.
    Stops when: max_rounds reached, either side concedes, or no new arguments.
    Returns transcript: [{"speaker": str, "content": str, "side": str}, ...]
    """
    mutated = [(n, o) for n, o in initial_vote_outputs if o.verdict.strip().lower() == "mutated"]
    faithful = [(n, o) for n, o in initial_vote_outputs if o.verdict.strip().lower() == "faithful"]

    if not mutated or not faithful:
        return []

    debate_config = config.get("debate", {})
    max_rounds = debate_config.get("max_rounds", 2)
    model_name = config.get("models", {}).get("agents", "gpt-4o-mini")
    llm = ChatOpenAI(model=model_name)
    template = load_jury_template("debate_template")
    status_prompt_tpl = load("jury/debate_status_check.txt")
    fact_frame_str = fact_frame.model_dump_json(indent=2)
    transcript: list[dict] = []
    status: DebateStatus | None = None

    mutated_args = "\n".join(f"{n}: {o.reasoning}" for n, o in mutated)
    faithful_args = "\n".join(f"{n}: {o.reasoning}" for n, o in faithful)

    for round_idx in range(max_rounds):
        # Mutated side speaks
        speaker, output = mutated[round_idx % len(mutated)]
        role_instruction = load_role_instruction(speaker)
        if round_idx == 0:
            debate_context = f"Faithful side's initial reasoning:\n{faithful_args}"
            round_instruction = ""
        else:
            debate_context = _format_transcript(transcript)
            round_instruction = "Focus on the most recent exchange."
        prompt = template.format(
            role_instruction=role_instruction.strip(),
            claim=claim,
            truth=truth,
            fact_frame=fact_frame_str,
            verdict="Mutated",
            reasoning=output.reasoning,
            debate_context=debate_context,
            round_instruction=round_instruction,
        )
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        transcript.append({"speaker": speaker, "content": content, "side": output.verdict})

        # Check concession
        should_stop, status = _should_stop(transcript, status_prompt_tpl, llm)
        if should_stop:
            transcript.append({"speaker": "Debate Status", "content": status})
            break

        # Faithful side speaks
        speaker, output = faithful[round_idx % len(faithful)]
        role_instruction = load_role_instruction(speaker)
        if round_idx == 0:
            debate_context = f"Mutated side's argument:\n{transcript[0]['content']}\n\nMutated reasoning:\n{mutated_args}"
            round_instruction = ""
        else:
            debate_context = _format_transcript(transcript)
            round_instruction = "Focus on the most recent exchange."
        prompt = template.format(
            role_instruction=role_instruction.strip(),
            claim=claim,
            truth=truth,
            fact_frame=fact_frame_str,
            verdict="Faithful",
            reasoning=output.reasoning,
            debate_context=debate_context,
            round_instruction=round_instruction,
        )
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        transcript.append({"speaker": speaker, "content": content, "side": output.verdict})

        # Check concession or no new arguments
        should_stop, status = _should_stop(transcript, status_prompt_tpl, llm)
        if should_stop:
            transcript.append({"speaker": "Debate Status", "content": status})
            break

    return transcript


def _format_transcript(transcript: list[dict]) -> str:
    lines = [f"{t['speaker']} (side: {t['side']}): {t['content']}" for t in transcript]
    return "Debate so far:\n" + "\n\n".join(lines)


def _should_stop(
    transcript: list[dict],
    prompt_template: str,
    llm: ChatOpenAI,
    
) -> tuple[bool, str | None]:
    """Check if debate should stop: conceded or no new arguments."""
    if len(transcript) < 2:
        return False, None
    formatted = "\n\n".join(
        f"{t['speaker']} (side: {t['side']}): {t['content']}" for t in transcript
    )
    prompt = prompt_template.format(transcript=formatted)
    checker = llm.with_structured_output(DebateStatus)
    status = checker.invoke(prompt)
    if status.conceded:
        return True, "Conceded"
    elif status.no_new_arguments:
        return True, "No new arguments"
    return False, "No decision. Debate continues..."