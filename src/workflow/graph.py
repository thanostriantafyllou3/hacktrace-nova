"""LangGraph pipeline: parse → initial_vote → [debate?] → revote → foreperson."""

from langgraph.graph import StateGraph
from langgraph.constants import START, END

from .state import JuryState
from .vote import run_vote, is_split
from .debate import run_debate
from agents import parse, run_foreperson


def _as_state(state: JuryState | dict) -> JuryState:
    """Normalize state to JuryState (LangGraph may pass a dict internally)."""
    if isinstance(state, JuryState):
        return state
    return JuryState.model_validate(state)


def _parse_node(state: JuryState) -> dict:
    s = _as_state(state)
    fact_frame = parse(s.claim, s.truth, s.config)
    return {"fact_frame": fact_frame}


def _initial_vote_node(state: JuryState) -> dict:
    s = _as_state(state)
    outputs = run_vote(s.claim, s.truth, s.fact_frame, s.config)
    return {"initial_vote_outputs": outputs}


def _route_after_initial_vote(state: JuryState) -> str:
    s = _as_state(state)
    return "split" if is_split(s.initial_vote_outputs or []) else "unanimous"


def _debate_node(state: JuryState) -> dict:
    s = _as_state(state)
    transcript = run_debate(
        s.initial_vote_outputs or [],
        s.claim,
        s.truth,
        s.fact_frame,
        s.config,
    )
    return {"transcript": transcript, "skipped_debate": False}


def _revote_node(state: JuryState) -> dict:
    s = _as_state(state)
    transcript = s.transcript or []
    outputs = run_vote(s.claim, s.truth, s.fact_frame, s.config, transcript=transcript)
    return {
        "revote_outputs": outputs,
        "skipped_debate": len(transcript) == 0,
        "transcript": transcript,  # ensure set when skipped
    }


def _foreperson_node(state: JuryState) -> dict:
    s = _as_state(state)
    config = s.config
    rubric = config.get("foreperson", {}).get("rubric", [])
    rubric_lines = [
        f"- {r['axis']}: {r['question']}" for r in rubric
    ]
    rubric_questions = "\n".join(rubric_lines)

    revote_str = "\n".join(
        f"{name}: {out.verdict} (confidence {out.confidence:.2f})\n  {out.reasoning}"
        for name, out in (s.revote_outputs or [])
    )
    transcript_str = "\n".join(
        f"{t.get('speaker', 'Agent')}: {t.get('content', '')}"
        for t in (s.transcript or [])
    ) or "(No debate)"

    verdict = run_foreperson(
        claim=s.claim,
        truth=s.truth,
        fact_frame_str=s.fact_frame.model_dump_json(indent=2),
        transcript_str=transcript_str,
        revote_outputs_str=revote_str,
        rubric_questions=rubric_questions,
        config=config,
    )
    return {"verdict": verdict}


def build_graph() -> StateGraph:
    """Build and compile the jury pipeline graph."""
    graph = StateGraph(JuryState)

    # Add nodes
    graph.add_node("parse", _parse_node)
    graph.add_node("initial_vote", _initial_vote_node)
    graph.add_node("debate", _debate_node)
    graph.add_node("revote", _revote_node)
    graph.add_node("foreperson", _foreperson_node)

    # Add edges
    graph.add_edge(START, "parse")
    graph.add_edge("parse", "initial_vote")
    graph.add_conditional_edges(
        "initial_vote",
        _route_after_initial_vote,
        {"split": "debate", "unanimous": "revote"},
    )
    graph.add_edge("debate", "revote")
    graph.add_edge("revote", "foreperson")
    graph.add_edge("foreperson", END)

    return graph.compile()


def run_pipeline(claim: str, truth: str, config: dict) -> dict:
    """Run the full jury pipeline on a (claim, truth) pair. Returns final state (dict)."""
    compiled = build_graph()
    return compiled.invoke({"claim": claim, "truth": truth, "config": config})


def run_pipeline_interactive(
    claim: str, truth: str, config: dict, *, print_fn=None
) -> dict:
    """
    Run the pipeline with interactive CLI output: shows parse, votes, debate, verdict.
    Uses streaming to print each step as it completes.
    """
    if print_fn is None:
        print_fn = print

    compiled = build_graph()
    initial = {"claim": claim, "truth": truth, "config": config}
    state = dict(initial)

    for chunk in compiled.stream(initial, stream_mode="updates"):
        for node_name, update in chunk.items():
            state.update(update)
            _print_step(node_name, update, state, print_fn)

    return state


def _print_step(node_name: str, update: dict, state: dict, print_fn):
    """Format and print one pipeline step."""
    if node_name == "parse":
        fact_frame = update.get("fact_frame")
        if fact_frame and hasattr(fact_frame, "facts"):
            print_fn("\n  📋 FACT FRAME (parsed from claim vs truth):")
            print_fn(f"    {len(fact_frame.facts)} facts extracted:")
            for i, fact in enumerate(fact_frame.facts, 1):
                cs = (fact.claim_says or "")
                ts = (fact.truth_says or "")
                note = f" [{fact.note}]" if fact.note else ""
                print_fn(f"    {i}. {fact.category}: claim=\"{cs}\" truth=\"{ts}\"{note}")

    elif node_name == "initial_vote":
        outputs = update.get("initial_vote_outputs", [])
        print_fn("\n  🗳️  INITIAL VOTE:")
        for name, out in outputs:
            icon = "✅" if out.verdict.strip().lower() == "faithful" else "❌"
            print_fn(f"    {icon} {name}: {out.verdict} (confidence {out.confidence:.2f})")
            print_fn(f"       └ {out.reasoning}")

    elif node_name == "debate":
        transcript = update.get("transcript", [])
        print_fn("\n  💬 DEBATE:")
        for t in transcript:
            speaker = t.get("speaker", "Agent")
            content = (t.get("content", "") or "").strip()
            print_fn(f"    {speaker}: {content}")
        if not transcript:
            print_fn("    (No debate - unanimous)")

    elif node_name == "revote":
        outputs = update.get("revote_outputs", [])
        skipped = update.get("skipped_debate")
        if skipped:
            print_fn("\n  🗳️  REVOTE (debate skipped - unanimous):")
        else:
            print_fn("\n  🗳️  REVOTE (after debate):")
        for name, out in outputs:
            icon = "✅" if out.verdict.strip().lower() == "faithful" else "❌"
            print_fn(f"    {icon} {name}: {out.verdict} (confidence {out.confidence:.2f})")
            print_fn(f"       └ {out.reasoning}")

    elif node_name == "foreperson":
        verdict = update.get("verdict")
        if verdict:
            print_fn("\n  ⚖️  VERDICT:")
            print_fn(f"    → {verdict.verdict} (confidence {verdict.confidence:.2f})")
            for ar in verdict.axis_results:
                mark = "✓" if ar.passed else "✗"
                print_fn(f"    {mark} {ar.axis}: {'Yes' if ar.passed else 'No'}" + (f" — {ar.note}" if ar.note else ""))
            print_fn(f"\n  Summary: {verdict.summary}")
            if verdict.minimal_edit:
                print_fn(f"  Minimal edit: {verdict.minimal_edit}")
            if verdict.dissent_note:
                print_fn(f"  Dissent: {verdict.dissent_note}")
