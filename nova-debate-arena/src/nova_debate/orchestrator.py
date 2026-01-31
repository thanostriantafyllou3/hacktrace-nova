from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from langchain_core.runnables import Runnable

from .agents import (
    build_advocate_chain,
    build_fact_checker_chain,
    build_judge_chain,
    build_rebuttal_chain,
    build_skeptic_chain,
    get_llm,
    parse_judge_json,
)
from .schemas import DebateResult, DebateTurn, JudgeVerdict


def _fmt_transcript(turns: List[DebateTurn]) -> str:
    """Flatten turns into a readable text block for the Judge."""
    blocks: List[str] = []
    for t in turns:
        blocks.append(f"[{t.agent}]\n{t.content}\n")
    return "\n".join(blocks)


async def _astream_text(chain: Runnable, vars: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """Stream text deltas from a LangChain Runnable.

    Works with chat model chunks (AIMessageChunk) or string chunks.
    """
    async for chunk in chain.astream(vars):
        if chunk is None:
            continue
        text = getattr(chunk, "content", None)
        if text is None:
            text = str(chunk)
        if not text:
            continue
        yield text


async def _stream_turn(
    *,
    agent: str,
    turn_id: str,
    chain: Runnable,
    vars: Dict[str, Any],
) -> AsyncGenerator[Dict[str, Any], None]:
    """Yield websocket-friendly events for a single agent turn."""

    yield {
        "type": "turn_start",
        "agent": agent,
        "turn_id": turn_id,
    }

    parts: List[str] = []
    async for delta in _astream_text(chain, vars):
        parts.append(delta)
        yield {
            "type": "turn_delta",
            "agent": agent,
            "turn_id": turn_id,
            "delta": delta,
        }

    content = "".join(parts).strip()
    yield {
        "type": "turn_end",
        "agent": agent,
        "turn_id": turn_id,
        "content": content,
    }


async def debate_events(
    *,
    row_id: int,
    claim: str,
    truth: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    rebuttal_rounds: int = 1,
    max_tokens: Optional[int] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Async event stream that powers the realtime UI.

    The UI can render events as a live cartoon debate.
    """

    # Use a streaming-enabled model so the UI can animate token-by-token.
    llm = get_llm(model=model, temperature=temperature, max_tokens=max_tokens, streaming=True)

    turns: List[DebateTurn] = []

    # Step 0: Case file
    moderator_text = (
        "### Case file\n"
        f"- **Row:** {row_id}\n"
        f"- **Truth (internal):** {truth}\n"
        f"- **Claim (external):** {claim}\n"
    )
    turns.append(DebateTurn(agent="Moderator", content=moderator_text))

    yield {
        "type": "case_file",
        "row_id": row_id,
        "truth": truth,
        "claim": claim,
    }

    advocate = build_advocate_chain(llm)
    skeptic = build_skeptic_chain(llm)
    factcheck = build_fact_checker_chain(llm)

    # Step 1: Opening statements
    yield {"type": "phase", "name": "Opening statements"}

    adv_text = ""
    async for e in _stream_turn(
        agent="Advocate",
        turn_id="advocate_opening",
        chain=advocate,
        vars={"truth": truth, "claim": claim},
    ):
        yield e
        if e["type"] == "turn_end":
            adv_text = str(e["content"])
            turns.append(DebateTurn(agent="Advocate", content=adv_text))

    sk_text = ""
    async for e in _stream_turn(
        agent="Skeptic",
        turn_id="skeptic_opening",
        chain=skeptic,
        vars={"truth": truth, "claim": claim},
    ):
        yield e
        if e["type"] == "turn_end":
            sk_text = str(e["content"])
            turns.append(DebateTurn(agent="Skeptic", content=sk_text))

    fc_text = ""
    async for e in _stream_turn(
        agent="Fact-Checker",
        turn_id="factcheck",
        chain=factcheck,
        vars={"truth": truth, "claim": claim},
    ):
        yield e
        if e["type"] == "turn_end":
            fc_text = str(e["content"])
            turns.append(DebateTurn(agent="Fact-Checker", content=fc_text))

    # Step 3: Rebuttal rounds
    for r in range(max(0, int(rebuttal_rounds))):
        yield {"type": "phase", "name": f"Rebuttal round {r+1}"}

        adv_reb = build_rebuttal_chain(llm, side="advocate")
        adv_reb_text = ""
        async for e in _stream_turn(
            agent=f"Advocate (rebuttal {r+1})",
            turn_id=f"advocate_rebuttal_{r+1}",
            chain=adv_reb,
            vars={
                "truth": truth,
                "claim": claim,
                "opponent": sk_text,
                "factcheck": fc_text,
            },
        ):
            yield e
            if e["type"] == "turn_end":
                adv_reb_text = str(e["content"])
                turns.append(DebateTurn(agent=f"Advocate (rebuttal {r+1})", content=adv_reb_text))

        sk_reb = build_rebuttal_chain(llm, side="skeptic")
        sk_reb_text = ""
        async for e in _stream_turn(
            agent=f"Skeptic (rebuttal {r+1})",
            turn_id=f"skeptic_rebuttal_{r+1}",
            chain=sk_reb,
            vars={
                "truth": truth,
                "claim": claim,
                "opponent": adv_reb_text,
                "factcheck": fc_text,
            },
        ):
            yield e
            if e["type"] == "turn_end":
                sk_reb_text = str(e["content"])
                turns.append(DebateTurn(agent=f"Skeptic (rebuttal {r+1})", content=sk_reb_text))

        adv_text, sk_text = adv_reb_text, sk_reb_text

    # Step 4: Verdict
    yield {"type": "phase", "name": "Verdict"}

    judge = build_judge_chain(llm)
    transcript = _fmt_transcript(turns)

    judge_raw = ""
    async for e in _stream_turn(
        agent="Judge",
        turn_id="judge",
        chain=judge,
        vars={"truth": truth, "claim": claim, "transcript": transcript},
    ):
        yield e
        if e["type"] == "turn_end":
            judge_raw = str(e["content"])

    verdict: JudgeVerdict
    try:
        verdict = parse_judge_json(judge_raw)
    except Exception as ex:
        # A very defensive fallback: if parsing fails, treat as mutated with low confidence.
        verdict = JudgeVerdict(
            verdict="MUTATED",
            confidence=0.2,
            one_sentence_summary="Judge output could not be parsed as JSON.",
            rationale=["The model did not return valid JSON for the verdict."],
            critical_differences=["(parsing failure)"],
            what_would_make_it_faithful=["Ensure the Judge prompt returns valid JSON."],
        )
        yield {
            "type": "error",
            "message": f"Could not parse judge JSON: {ex}",
        }

    turns.append(
        DebateTurn(
            agent="Judge",
            content=json.dumps(verdict.model_dump(), indent=2),
            metadata={"raw": judge_raw},
        )
    )

    yield {
        "type": "verdict",
        "verdict": verdict.model_dump(),
    }

    yield {"type": "done"}


async def run_debate_collect(
    *,
    row_id: int,
    claim: str,
    truth: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    rebuttal_rounds: int = 1,
    max_tokens: Optional[int] = None,
) -> DebateResult:
    """Collect the streamed events into a DebateResult (useful for CLI/batch)."""

    turns: List[DebateTurn] = [
        DebateTurn(
            agent="Moderator",
            content=(
                "### Case file\n"
                f"- **Row:** {row_id}\n"
                f"- **Truth (internal):** {truth}\n"
                f"- **Claim (external):** {claim}\n"
            ),
        )
    ]

    verdict: Optional[JudgeVerdict] = None

    async for e in debate_events(
        row_id=row_id,
        claim=claim,
        truth=truth,
        model=model,
        temperature=temperature,
        rebuttal_rounds=rebuttal_rounds,
        max_tokens=max_tokens,
    ):
        if e.get("type") == "turn_end":
            turns.append(DebateTurn(agent=str(e["agent"]), content=str(e["content"])))
        if e.get("type") == "verdict":
            verdict = JudgeVerdict.model_validate(e["verdict"])

    return DebateResult(row_id=row_id, claim=claim, truth=truth, turns=turns, verdict=verdict)
