# Eval and Error Analysis Plan

Based on M4: Practical Tips for Building Agentic AI (Andrew Ng). Our jury system is evaluated against ground truth and compared to a single stronger model baseline.

---

## Development Process (from M4)

1. **Build** end-to-end system
2. **Analyze** outputs and traces
3. **Build evals** and compute metrics
4. **Error analysis** — which component failed?
5. **Component-level evals** — target weak spots
6. **Improve** individual components

---

## Two Axes of Evaluation

| Axis | When | Example |
|------|------|---------|
| **Evaluate with code (objective)** | Per-example ground truth | Compare verdict to labeled Faithful/Mutated |
| **LLM-as-judge (subjective)** | No ground truth | Grade explanation quality, rubric coherence |

For this project we use **code-based evals** first (ground truth from dataset analysis), with optional LLM-as-judge for explanation quality later.

---

## Ground Truth

Derived from `DATASET_ANALYSIS.md`:

- **Faithful:** Pairs 6, 7, 8 (no material change)
- **Mutated:** All others (1–5, 9–15) — any mutation type implies Mutated

Ground truth file: `eval/ground_truth.json` — `{pair_id: "Faithful"|"Mutated"}`

---

## Eval Set

- **Size:** All 15 Nova pairs (or subset for quick iteration)
- **Quick iteration:** 5–10 pairs; full run: 15
- Config: `eval.pair_ids` or use `data.pair_ids` for consistency

---

## Metrics

| Metric | Description |
|--------|-------------|
| **Accuracy** | % correct verdicts (Faithful/Mutated) |
| **Cost per pair** | Total $ for LLM calls (input + output tokens × price) |
| **Latency per pair** | End-to-end seconds |
| **By mutation type** | Accuracy on hard_contradiction, entailed_but_coarsened, etc. |

---

## Baseline: Single Stronger Model

- **Model:** e.g. `gpt-4o` (or configurable)
- **Prompt:** "Given this claim and truth, is the claim Faithful or Mutated? Answer with one word."
- **Purpose:** Compare jury system vs single model on accuracy, cost, latency

---

## Error Analysis (from M4)

1. **Look at traces** — parse → initial_vote → debate → revote → foreperson
2. **Count errors by component** — where did the wrong verdict originate?
   - Parser: Bad fact extraction? (harder to attribute)
   - Initial vote: Wrong individual votes?
   - Debate: Did debate help or hurt?
   - Foreperson: Wrong rubric application?
3. **Focus on failures** — run eval only on pairs where system was wrong
4. **Component-level evals** — e.g. parser extraction quality, foreperson rubric adherence

---

## Implementation

- `eval/ground_truth.json` — ground truth labels
- `eval/run_eval.py` — runs jury system + baseline, computes metrics, saves traces
- `eval/error_analysis.py` — loads traces, counts errors by component (manual + automated)
- Traces saved to `eval/traces/` for inspection

---

## Cost Estimation

| Component | Calls per pair | Model | Est. cost/pair |
|-----------|----------------|-------|----------------|
| Parser | 1 | gpt-4.1-mini | ~$0.001 |
| Jury (4 agents × 2 rounds) | 4–8 | gpt-4.1-mini | ~$0.01 |
| Debate (2 speakers × rounds) | 2–4 | gpt-4.1-mini | ~$0.005 |
| Debate status | 1–2 | gpt-4.1-mini | ~$0.001 |
| Foreperson | 1 | gpt-4.1-mini | ~$0.002 |
| **Jury total** | | | **~$0.02** |
| **Baseline (1 call)** | 1 | gpt-4o | ~$0.01–0.03 |

Exact costs depend on token counts; run eval with token tracking for real numbers.
