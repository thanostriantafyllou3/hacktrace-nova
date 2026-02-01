"""Initial vote and revote: jury agents run in parallel, no cross-talk."""

from langchain_core.runnables import RunnableLambda, RunnableParallel

from schemas import FactFrame, JuryOutput

from agents import run_jury


def _make_agent_runnable(agent_name: str) -> RunnableLambda:
    """Wrap run_jury as a LangChain Runnable for a specific agent."""

    def _invoke(inputs: dict) -> JuryOutput:
        return run_jury(
            agent_name,
            inputs["claim"],
            inputs["truth"],
            inputs["fact_frame"],
            inputs["config"],
            transcript=inputs.get("transcript"),
        )

    return RunnableLambda(_invoke)


def run_vote(
    claim: str,
    truth: str,
    fact_frame: FactFrame,
    config: dict,
    transcript: list[dict] | None = None,
) -> list[tuple[str, JuryOutput]]:
    """
    Run all jury agents in parallel. Pass transcript for revote (after debate).

    Returns:
        List of (agent_name, output) in config order.
    """
    agent_cfgs = config.get("agents", [])
    if not agent_cfgs:
        return []

    branches = {cfg["name"]: _make_agent_runnable(cfg["name"]) for cfg in agent_cfgs}
    parallel = RunnableParallel(**branches)

    inputs = {
        "claim": claim,
        "truth": truth,
        "fact_frame": fact_frame,
        "config": config,
        "transcript": transcript or [],
    }
    result = parallel.invoke(inputs)
    return [(cfg["name"], result[cfg["name"]]) for cfg in agent_cfgs]


def is_split(outputs: list[tuple[str, JuryOutput]]) -> bool:
    """True if agents disagree (some Faithful, some Mutated)."""
    if not outputs:
        return False
    verdicts = [output.verdict.strip().lower() for _, output in outputs]
    return not all(verdict == verdicts[0] for verdict in verdicts)
