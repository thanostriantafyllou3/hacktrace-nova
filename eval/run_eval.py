"""
Eval script: compare jury system vs single-model baseline.

Usage (from project root):
  uv run python eval/run_eval.py

Uses ground truth from eval/ground_truth.json (derived from DATASET_ANALYSIS.md).
Saves traces to eval/traces/ for error analysis.
Tracks token usage and costs via LangChain's get_openai_callback (built-in pricing).
"""

import json
import sys
import time
from pathlib import Path

# Add src to path so we can import from config, workflow, etc.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from langchain_community.callbacks import get_openai_callback

from config import load_config
from workflow import run_pipeline


# --- Ground truth ---

def load_ground_truth() -> dict[int, str]:
    """Load ground truth: {pair_id: "Faithful"|"Mutated"}."""
    path = PROJECT_ROOT / "eval" / "ground_truth.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {int(k): v for k, v in data.items() if not k.startswith("_")}


# --- Baseline: single stronger model ---

def run_baseline(claim: str, truth: str, model: str = "gpt-4o") -> str:
    """Single LLM call: claim + truth -> Faithful or Mutated."""
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=model, temperature=0)
    prompt = f"""You are a fact-checker. Given an internal fact (truth) and an external claim, decide if the claim is a FAITHFUL representation of the truth or a MUTATION (distortion, exaggeration, omission, etc.).

TRUTH: {truth}

CLAIM: {claim}

Answer with exactly one word: Faithful or Mutated."""
    response = llm.invoke(prompt)
    text = (response.content or "").strip().upper()
    return "Mutated" if "MUTAT" in text else "Faithful"


# --- Eval ---

def normalize_verdict(v: str) -> str:
    """Normalize verdict to Faithful or Mutated."""
    v = (v or "").strip().lower()
    if "mutat" in v:
        return "Mutated"
    return "Faithful"


def run_eval(pair_ids: list[int] | None = None, baseline_model: str = "gpt-4o") -> None:
    """
    Run eval: jury system + baseline on pairs, compute metrics, save traces.
    """
    config = load_config()
    config["interactive"] = False

    # Load pairs
    config["data"] = config.get("data", {}) | {"source": "data/Nova.csv", "claim_col": "claim", "truth_col": "truth"}
    if pair_ids is not None:
        config["data"]["pair_ids"] = pair_ids
    else:
        config["data"]["pair_ids"] = list(range(15))  # All Nova pairs

    from data import load_pairs

    pairs = load_pairs(config)
    ground_truth = load_ground_truth()

    traces_dir = PROJECT_ROOT / "eval" / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)

    jury_results = []
    baseline_results = []

    print("=" * 60)
    print("EVAL: Jury System vs Single-Model Baseline")
    print("=" * 60)
    print(f"Pairs: {[p['id'] for p in pairs]}")
    print(f"Baseline model: {baseline_model}")
    print()

    for pair in pairs:
        pid = pair["id"]
        claim = pair["claim"]
        truth = pair["truth"]
        expected = ground_truth.get(pid)

        if expected is None:
            print(f"  [SKIP] Pair {pid}: no ground truth")
            continue

        # --- Jury system ---
        state = None
        t0 = time.perf_counter()
        jury_cost = 0.0
        jury_tokens = 0
        try:
            with get_openai_callback() as cb:
                state = run_pipeline(claim, truth, config)
            jury_time = time.perf_counter() - t0
            jury_cost = cb.total_cost
            jury_tokens = cb.total_tokens
            verdict_obj = state.get("verdict")
            jury_verdict = normalize_verdict(verdict_obj.verdict) if verdict_obj else "?"
        except Exception as e:
            jury_time = time.perf_counter() - t0
            jury_verdict = "?"
            print(f"  [JURY ERROR] Pair {pid}: {e}")

        jury_correct = jury_verdict == expected if jury_verdict != "?" else False
        jury_results.append({
            "id": pid,
            "verdict": jury_verdict,
            "expected": expected,
            "correct": jury_correct,
            "time_s": jury_time,
            "cost_usd": jury_cost,
            "total_tokens": jury_tokens,
        })

        # --- Baseline ---
        t0 = time.perf_counter()
        baseline_cost = 0.0
        baseline_tokens = 0
        try:
            with get_openai_callback() as cb:
                baseline_verdict = run_baseline(claim, truth, baseline_model)
            baseline_time = time.perf_counter() - t0
            baseline_cost = cb.total_cost
            baseline_tokens = cb.total_tokens
        except Exception as e:
            baseline_time = time.perf_counter() - t0
            baseline_verdict = "?"
            print(f"  [BASELINE ERROR] Pair {pid}: {e}")

        baseline_correct = baseline_verdict == expected if baseline_verdict != "?" else False
        baseline_results.append({
            "id": pid,
            "verdict": baseline_verdict,
            "expected": expected,
            "correct": baseline_correct,
            "time_s": baseline_time,
            "cost_usd": baseline_cost,
            "total_tokens": baseline_tokens,
        })

        # Save trace for error analysis
        trace = {
            "pair_id": pid,
            "claim": claim[:200] + "..." if len(claim) > 200 else claim,
            "truth": truth[:200] + "..." if len(truth) > 200 else truth,
            "expected": expected,
            "jury_verdict": jury_verdict,
            "jury_correct": jury_correct,
            "jury_time_s": jury_time,
            "jury_cost_usd": jury_cost,
            "jury_tokens": jury_tokens,
            "baseline_verdict": baseline_verdict,
            "baseline_correct": baseline_correct,
            "baseline_time_s": baseline_time,
            "baseline_cost_usd": baseline_cost,
            "baseline_tokens": baseline_tokens,
        }
        if state:
            v = state.get("verdict")
            # Foreperson output (full Verdict)
            if v:
                trace["foreperson"] = {
                    "verdict": v.verdict,
                    "confidence": v.confidence,
                    "summary": v.summary,
                    "minimal_edit": v.minimal_edit,
                    "dissent_note": v.dissent_note,
                    "axis_results": [
                        {"axis": ar.axis, "passed": ar.passed, "note": ar.note}
                        for ar in (v.axis_results or [])
                    ],
                }
            else:
                trace["foreperson"] = None
            # Keep backward-compat keys
            trace["jury_summary"] = v.summary if v else None
            trace["jury_axis_results"] = [{"axis": ar.axis, "passed": ar.passed} for ar in (v.axis_results or [])] if v else []
            
            # Initial votes: full outputs with reasoning, confidence, evidence
            initial_outputs = state.get("initial_vote_outputs") or []
            trace["initial_votes"] = [
                {
                    "agent": name,
                    "verdict": output.verdict,
                    "confidence": output.confidence,
                    "reasoning": output.reasoning,
                    "evidence": [
                        {
                            "fact": ev.fact.model_dump(),
                            "issue": ev.issue,
                        }
                        for ev in output.evidence
                    ],
                }
                for name, output in initial_outputs
            ]
            
            # Revote votes: full outputs with reasoning, confidence, evidence
            revote_outputs = state.get("revote_outputs") or []
            trace["revote_votes"] = [
                {
                    "agent": name,
                    "verdict": output.verdict,
                    "confidence": output.confidence,
                    "reasoning": output.reasoning,
                    "evidence": [
                        {
                            "fact": ev.fact.model_dump(),
                            "issue": ev.issue,
                        }
                        for ev in output.evidence
                    ],
                }
                for name, output in revote_outputs
            ]
            
            # Debate: full transcript and status
            trace["debate_ran"] = bool(state.get("transcript"))
            trace["debate_transcript"] = state.get("transcript") or []
            trace["debate_status"] = state.get("debate_status")
            trace["debate_round_idx"] = state.get("debate_round_idx", 0)
            trace["skipped_debate"] = state.get("skipped_debate", False)
            
            # Fact frame (parser output)
            fact_frame = state.get("fact_frame")
            if fact_frame:
                trace["fact_frame"] = fact_frame.model_dump()

        with open(traces_dir / f"pair_{pid}.json", "w", encoding="utf-8") as f:
            json.dump(trace, f, indent=2)

        mark_j = "✓" if jury_correct else "✗"
        mark_b = "✓" if baseline_correct else "✗"
        print(f"  Pair {pid}: expected={expected}  jury={jury_verdict} {mark_j}  baseline={baseline_verdict} {mark_b}")

    # --- Metrics ---
    n = len(jury_results)
    jury_acc = sum(1 for r in jury_results if r["correct"]) / n if n else 0
    baseline_acc = sum(1 for r in baseline_results if r["correct"]) / n if n else 0
    jury_avg_time = sum(r["time_s"] for r in jury_results) / n if n else 0
    baseline_avg_time = sum(r["time_s"] for r in baseline_results) / n if n else 0
    jury_total_cost = sum(r["cost_usd"] for r in jury_results)
    baseline_total_cost = sum(r["cost_usd"] for r in baseline_results)
    jury_total_tokens = sum(r["total_tokens"] for r in jury_results)
    baseline_total_tokens = sum(r["total_tokens"] for r in baseline_results)
    jury_cost_per_pair = jury_total_cost / n if n else 0
    baseline_cost_per_pair = baseline_total_cost / n if n else 0

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"  Accuracy:    Jury {jury_acc:.1%}  |  Baseline {baseline_acc:.1%}")
    print(f"  Avg time:    Jury {jury_avg_time:.1f}s  |  Baseline {baseline_avg_time:.1f}s")
    print(f"  Cost/pair:   Jury ${jury_cost_per_pair:.4f}  |  Baseline ${baseline_cost_per_pair:.4f}")
    print(f"  Total cost:  Jury ${jury_total_cost:.4f}  |  Baseline ${baseline_total_cost:.4f}")
    print(f"  Total tokens: Jury {jury_total_tokens:,}  |  Baseline {baseline_total_tokens:,}")
    print(f"  Traces:      eval/traces/")
    print("  (Costs from LangChain built-in OpenAI pricing)")
    print()

    # Save complete summary to traces directory
    summary_path = traces_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "num_pairs": n,
                "accuracy": {
                    "jury": jury_acc,
                    "baseline": baseline_acc,
                },
                "avg_time_s": {
                    "jury": jury_avg_time,
                    "baseline": baseline_avg_time,
                },
                "cost_per_pair_usd": {
                    "jury": jury_cost_per_pair,
                    "baseline": baseline_cost_per_pair,
                },
                "total_cost_usd": {
                    "jury": jury_total_cost,
                    "baseline": baseline_total_cost,
                },
                "total_tokens": {
                    "jury": jury_total_tokens,
                    "baseline": baseline_total_tokens,
                },
                "note": "Costs from LangChain built-in OpenAI pricing",
            },
            f,
            indent=2,
        )
    print(f"  Summary saved to: {summary_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=str, default=None, help="Comma-separated pair IDs, e.g. 0,5,9. Default: from config or all 15")
    parser.add_argument("--baseline", type=str, default=None, help="Baseline model. Default: from config or gpt-4o")
    args = parser.parse_args()

    config = load_config()
    eval_cfg = config.get("eval", {})

    pair_ids = None
    if args.pairs:
        pair_ids = [int(x.strip()) for x in args.pairs.split(",")]
    elif "pair_ids" in eval_cfg:
        pair_ids = eval_cfg["pair_ids"]

    baseline_model = args.baseline or eval_cfg.get("baseline_model", "gpt-4o")

    run_eval(pair_ids=pair_ids, baseline_model=baseline_model)
