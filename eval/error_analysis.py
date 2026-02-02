"""
Error analysis: inspect traces for pairs where the jury was wrong, count errors by component, focus improvement efforts.

Usage (from project root):
  uv run python eval/error_analysis.py
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_traces() -> list[dict]:
    """Load all trace files from eval/traces/."""
    traces_dir = PROJECT_ROOT / "eval" / "traces"
    if not traces_dir.exists():
        print("No traces found. Run: uv run python eval/run_eval.py")
        return []

    traces = []
    for f in sorted(traces_dir.glob("pair_*.json")):
        with open(f, encoding="utf-8") as fp:
            traces.append(json.load(fp))
    return traces


def run_analysis() -> None:
    traces = load_traces()
    if not traces:
        return

    failures = [t for t in traces if not t.get("jury_correct", True)]
    if not failures:
        print("No jury failures. All pairs correct.")
        return

    print("=" * 70)
    print("ERROR ANALYSIS: Jury failures (expected vs predicted)")
    print("=" * 70)
    print(f"Total pairs: {len(traces)}  |  Failures: {len(failures)}")
    print()

    for t in failures:
        pid = t["pair_id"]
        expected = t["expected"]
        got = t["jury_verdict"]
        print(f"--- Pair {pid}: expected {expected}, got {got} ---")
        print(f"  Claim: {t.get('claim', '')[:120]}...")
        
        # Initial votes with confidence
        if "initial_votes" in t and t["initial_votes"]:
            if isinstance(t["initial_votes"][0], dict):
                votes_str = ", ".join(
                    f"{v['agent']}={v['verdict']}({v.get('confidence', 0):.2f})"
                    for v in t["initial_votes"]
                )
                print(f"  Initial votes: {votes_str}")
                
                # Show which agents were wrong initially
                wrong_agents = [
                    v["agent"] for v in t["initial_votes"]
                    if v.get("verdict", "").lower() != expected.lower()
                ]
                if wrong_agents:
                    print(f"    Wrong agents: {', '.join(wrong_agents)}")
            else:
                votes = ", ".join(f"{n}={v}" for n, v in t["initial_votes"])
                print(f"  Initial votes: {votes}")
        
        # Revote votes with confidence
        if "revote_votes" in t and t["revote_votes"]:
            if isinstance(t["revote_votes"][0], dict):
                votes_str = ", ".join(
                    f"{v['agent']}={v['verdict']}({v.get('confidence', 0):.2f})"
                    for v in t["revote_votes"]
                )
                print(f"  Revote votes:  {votes_str}")
                
                # Check if debate changed any votes
                if isinstance(t.get("initial_votes", []), list) and t["initial_votes"]:
                    if isinstance(t["initial_votes"][0], dict):
                        initial_dict = {v["agent"]: v["verdict"] for v in t["initial_votes"]}
                        revote_dict = {v["agent"]: v["verdict"] for v in t["revote_votes"]}
                        changed = [
                            agent for agent in initial_dict
                            if initial_dict[agent] != revote_dict.get(agent)
                        ]
                        if changed:
                            print(f"    Votes changed after debate: {', '.join(changed)}")
            else:
                votes = ", ".join(f"{n}={v}" for n, v in t["revote_votes"])
                print(f"  Revote votes:  {votes}")
        
        # Debate analysis
        if "debate_ran" in t:
            print(f"  Debate ran: {t['debate_ran']}")
            if t.get("debate_transcript"):
                print(f"    Rounds: {t.get('debate_round_idx', 0)}")
                print(f"    Status: {t.get('debate_status', 'N/A')}")
                # Show debate length
                transcript = t.get("debate_transcript", [])
                if transcript:
                    print(f"    Transcript length: {len(transcript)} messages")
        
        # Foreperson output
        fp = t.get("foreperson")
        if fp:
            print(f"  Foreperson: verdict={fp.get('verdict')}, confidence={fp.get('confidence', 0):.2f}")
            if fp.get("dissent_note"):
                print(f"    Dissent note: {fp['dissent_note'][:150]}...")
            if fp.get("minimal_edit"):
                print(f"    Minimal edit: {fp['minimal_edit'][:150]}...")
            # Axis results with notes
            axis_results = fp.get("axis_results") or []
            failed_axes = [ar for ar in axis_results if not ar.get("passed")]
            if failed_axes:
                print(f"  Failed rubric axes:")
                for ar in failed_axes:
                    note = f" — {ar['note']}" if ar.get("note") else ""
                    print(f"    {ar['axis']}{note}")
            passed_all = all(ar.get("passed") for ar in axis_results) if axis_results else False
            if passed_all and got != expected:
                print(f"  All axes passed (but verdict was wrong!)")
        elif "jury_axis_results" in t and t["jury_axis_results"]:
            # Fallback to legacy format
            failed_axes = [ar["axis"] for ar in t["jury_axis_results"] if not ar.get("passed")]
            passed_axes = [ar["axis"] for ar in t["jury_axis_results"] if ar.get("passed")]
            if failed_axes:
                print(f"  Failed rubric axes: {', '.join(failed_axes)}")
            if passed_axes and not failed_axes:
                print(f"  All axes passed (but verdict was wrong!)")
        
        # Show reasoning from wrong agents
        if "initial_votes" in t and isinstance(t["initial_votes"], list) and t["initial_votes"]:
            if isinstance(t["initial_votes"][0], dict):
                wrong_reasoning = [
                    (v["agent"], v.get("reasoning", ""))
                    for v in t["initial_votes"]
                    if v.get("verdict", "").lower() != expected.lower()
                ]
                if wrong_reasoning:
                    print(f"  Wrong agents' reasoning:")
                    for agent, reasoning in wrong_reasoning[:2]:  # Show first 2
                        print(f"    {agent}: {reasoning[:200]}...")
        
        # Foreperson summary (from foreperson or legacy jury_summary)
        summary = (fp.get("summary") if fp else None) or t.get("jury_summary")
        if summary:
            print(f"  Foreperson summary: {summary[:200]}...")
        print()

    # Component-level hints (from M4: count errors by component)
    print("=" * 70)
    print("COMPONENT HINTS (where to focus)")
    print("=" * 70)
    unanim_initial = sum(1 for t in failures if _all_same(t.get("initial_votes", [])) and t.get("initial_votes"))
    split_initial = len(failures) - unanim_initial
    if failures:
        print(f"  Failures with unanimous initial vote: {unanim_initial} (parser/agents may have missed signal)")
        print(f"  Failures with split initial vote:     {split_initial} (debate/revote/foreperson may be at fault)")
    
    # Analyze confidence patterns
    low_confidence_count = 0
    high_confidence_wrong = 0
    for t in failures:
        if isinstance(t.get("initial_votes"), list) and t["initial_votes"]:
            if isinstance(t["initial_votes"][0], dict):
                wrong_votes = [
                    v for v in t["initial_votes"]
                    if v.get("verdict", "").lower() != t.get("expected", "").lower()
                ]
                if wrong_votes:
                    avg_conf = sum(v.get("confidence", 0) for v in wrong_votes) / len(wrong_votes)
                    if avg_conf < 0.7:
                        low_confidence_count += 1
                    elif avg_conf > 0.8:
                        high_confidence_wrong += 1
    
    if low_confidence_count > 0:
        print(f"  Failures with low confidence wrong votes: {low_confidence_count} (agents uncertain)")
    if high_confidence_wrong > 0:
        print(f"  Failures with high confidence wrong votes: {high_confidence_wrong} (agents overconfident)")
    
    # Debate impact analysis
    debate_helped = 0
    debate_hurt = 0
    for t in failures:
        if isinstance(t.get("initial_votes"), list) and isinstance(t.get("revote_votes"), list):
            if t["initial_votes"] and t["revote_votes"]:
                if isinstance(t["initial_votes"][0], dict) and isinstance(t["revote_votes"][0], dict):
                    initial_correct = sum(
                        1 for v in t["initial_votes"]
                        if v.get("verdict", "").lower() == t.get("expected", "").lower()
                    )
                    revote_correct = sum(
                        1 for v in t["revote_votes"]
                        if v.get("verdict", "").lower() == t.get("expected", "").lower()
                    )
                    if revote_correct > initial_correct:
                        debate_helped += 1
                    elif revote_correct < initial_correct:
                        debate_hurt += 1
    
    if debate_helped > 0 or debate_hurt > 0:
        print(f"  Debate helped (more correct votes): {debate_helped}")
        print(f"  Debate hurt (fewer correct votes): {debate_hurt}")
    
    # Failed axes frequency (prefer foreperson.axis_results, fallback to jury_axis_results)
    failed_axes_count = {}
    for t in failures:
        axis_results = (
            t.get("foreperson", {}).get("axis_results")
            or t.get("jury_axis_results", [])
        )
        for ar in axis_results:
            if not ar.get("passed"):
                axis = ar.get("axis", "unknown")
                failed_axes_count[axis] = failed_axes_count.get(axis, 0) + 1
    
    if failed_axes_count:
        print(f"\n  Most failed rubric axes:")
        for axis, count in sorted(failed_axes_count.items(), key=lambda x: -x[1]):
            print(f"    {axis}: {count} failures")
    
    # Foreperson analysis: high confidence wrong verdicts, dissent cases
    foreperson_high_conf_wrong = sum(
        1 for t in failures
        if t.get("foreperson", {}).get("confidence", 0) > 0.8
    )
    foreperson_dissent = sum(
        1 for t in failures
        if t.get("foreperson", {}).get("dissent_note")
    )
    if foreperson_high_conf_wrong > 0:
        print(f"\n  Foreperson high confidence wrong: {foreperson_high_conf_wrong} (rubric may need tuning)")
    if foreperson_dissent > 0:
        print(f"  Failures with jury dissent: {foreperson_dissent} (foreperson overrode minority?)")
    
    print()
    print("  Next steps: Inspect traces in eval/traces/, improve prompts or rubric for weak axes.")


def _all_same(votes: list) -> bool:
    """Check if all votes are the same. Handles both tuple and dict formats."""
    if not votes or len(votes) < 2:
        return True
    
    # Handle new dict format
    if isinstance(votes[0], dict):
        v0 = (votes[0].get("verdict") or "").strip().lower()
        return all((v.get("verdict") or "").strip().lower() == v0 for v in votes)
    
    # Handle old tuple format
    v0 = (votes[0][1] or "").strip().lower()
    return all((v or "").strip().lower() == v0 for _, v in votes)


if __name__ == "__main__":
    run_analysis()
