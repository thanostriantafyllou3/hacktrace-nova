from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .schemas import JudgeVerdict


# Load .env if present (FastAPI / CLI friendly)
load_dotenv(override=False)


SYSTEM_GUARDRAILS = """You are part of a multi-agent jury evaluating whether an EXTERNAL CLAIM faithfully represents an INTERNAL FACT (truth).

Hard rules:
- Use ONLY the provided truth text. Do not rely on external knowledge.
- If the truth does not support the claim, say so explicitly.
- Call out changes in: numbers, dates, locations, entities, scope (countries vs countries+territories), and qualifiers ("more than", "under", "as of").
- Be precise. Quote short fragments from the truth when helpful.
- Keep your answer readable in Markdown.
"""


def get_llm(
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
    *,
    streaming: bool = False,
) -> ChatOpenAI:
    """Create a ChatOpenAI LLM configured via env or UI."""

    model = model or os.getenv("NOVA_MODEL") or "gpt-4o-mini"

    kwargs: Dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "streaming": streaming,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    # NOTE: users can set OPENAI_API_KEY via env/.env
    return ChatOpenAI(**kwargs)


def build_advocate_chain(llm: ChatOpenAI):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_GUARDRAILS + "\n\nRole: ADVOCATE (argue the claim is faithful)."),
            (
                "human",
                """INTERNAL FACT (truth):
{truth}

EXTERNAL CLAIM:
{claim}

Task:
- Argue that the claim is a faithful representation of the truth.
- Provide 2-3 bullet points maximum.
- If there are differences, frame whether they are minor (rounding, rephrasing) or potentially meaningful.
- Keep your response to 3 sentences maximum.
- End with a 1-line stance: **Stance:** Faithful / Partially / Mutated (your best guess, even though you argue faithful).
""",
            ),
        ]
    )
    return prompt | llm


def build_skeptic_chain(llm: ChatOpenAI):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_GUARDRAILS + "\n\nRole: SKEPTIC (argue the claim is mutated / misleading)."),
            (
                "human",
                """INTERNAL FACT (truth):
{truth}

EXTERNAL CLAIM:
{claim}

Task:
- Argue that the claim is NOT a faithful representation.
- Provide 2-3 bullet points maximum of the most *meaning-changing* differences.
- Identify the smallest change that would make the claim faithful.
- Keep your response to 3 sentences maximum.
- End with a 1-line stance: **Stance:** Faithful / Partially / Mutated (your best guess).
""",
            ),
        ]
    )
    return prompt | llm


def build_fact_checker_chain(llm: ChatOpenAI):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_GUARDRAILS + "\n\nRole: FACT-CHECKER (extract and compare constraints)."),
            (
                "human",
                """INTERNAL FACT (truth):
{truth}

EXTERNAL CLAIM:
{claim}

Task:
1) Extract *from each*:
   - Numbers + units
   - Dates / time windows
   - Locations / entities
   - Qualifiers (more than / less than / under / as of / before)
2) Compare them in a compact checklist.
3) Conclude with:
   - **Mismatch severity:** minor / moderate / critical
   - 1-2 sentences on whether meaning changed.

Output format (Markdown):
- A compact table with columns: Dimension | Claim | Truth | Match?
- Keep total response to 3 sentences maximum (excluding table).
- Then the short conclusion.
""",
            ),
        ]
    )
    return prompt | llm


def build_rebuttal_chain(llm: ChatOpenAI, side: str):
    role = "ADVOCATE" if side == "advocate" else "SKEPTIC"
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_GUARDRAILS + f"\n\nRole: {role} (rebuttal)."),
            (
                "human",
                """INTERNAL FACT (truth):
{truth}

EXTERNAL CLAIM:
{claim}

Opponent's argument:
{opponent}

Fact-checker's notes:
{factcheck}

Task:
- Respond in 2-3 bullets maximum.
- Address the strongest point from the opponent.
- Keep your response to 3 sentences maximum.
- If you concede something, say what it changes.
- End with **Updated stance:** Faithful / Partially / Mutated.
""",
            ),
        ]
    )
    return prompt | llm


def build_judge_chain(llm: ChatOpenAI):
    # We ask for JSON to make the UI clean. We'll parse with a best-effort json loader.
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                SYSTEM_GUARDRAILS
                + "\n\nRole: JUDGE (neutral). You must output ONLY valid JSON, no extra text.",
            ),
            (
                "human",
                """You are judging whether the EXTERNAL CLAIM faithfully represents the INTERNAL FACT.

INTERNAL FACT (truth):
{truth}

EXTERNAL CLAIM:
{claim}

FULL DEBATE TRANSCRIPT:
{transcript}

Decide the final label:
- FAITHFUL
- PARTIALLY_FAITHFUL
- MUTATED

Return ONLY a JSON object with these keys:
- verdict: one of [FAITHFUL, PARTIALLY_FAITHFUL, MUTATED]
- confidence: number from 0 to 1
- one_sentence_summary: string
- rationale: array of 3-6 short bullets (strings)
- critical_differences: array of strings (may be empty)
- what_would_make_it_faithful: array of strings (may be empty)

Important:
- If there is an entity swap (wrong person/state/country), that is typically MUTATED.
- If differences are just rounding or "as of" date alignment, that may still be FAITHFUL or PARTIALLY.
""",
            ),
        ]
    )
    return prompt | llm


def parse_judge_json(text: str) -> JudgeVerdict:
    """Best-effort JSON parser for the judge output."""

    # First try direct JSON
    try:
        data = json.loads(text)
        return JudgeVerdict.model_validate(data)
    except Exception:
        pass

    # Try to extract the first JSON object substring
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            return JudgeVerdict.model_validate(data)
        except Exception as e:
            raise ValueError(f"Could not parse judge JSON. Raw output: {text}") from e

    raise ValueError(f"Could not parse judge JSON. Raw output: {text}")
