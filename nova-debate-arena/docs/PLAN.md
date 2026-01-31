# Plan: How the Nova Jury Judges & Debates

## Problem framing
Each row is a pair:

- **Truth (internal fact)**: the source statement.
- **Claim (external claim)**: a derived statement (headline / paraphrase / summary).

Goal: decide whether the claim is a **faithful representation** of the truth, or a **mutation** (meaning changed via exaggeration, missing qualifiers, wrong entity, wrong time, wrong number, etc.).

## Core idea: “jury” > “single prompt”
Instead of asking one model for a label, we stage a debate between agents with **different incentives**:

1. **Advocate** (argue *faithful*)
2. **Skeptic** (argue *mutated*)
3. **Fact‑Checker** (extract & compare hard constraints: numbers/dates/entities/scope)
4. **Judge** (weigh arguments; issue verdict + confidence)

This makes disagreements explicit, forces both sides to surface evidence, and reduces silent failure.

## Decision taxonomy
The Judge must output exactly one:

- **FAITHFUL** – meaning preserved; any differences are minor (rounding, synonym, rephrasing).
- **PARTIALLY_FAITHFUL** – mostly consistent, but missing key context or slightly misleading emphasis.
- **MUTATED** – key meaning changed (wrong number, time window, geography, entity, causal claim, or omitted qualifier that flips interpretation).

## Debate loop (per claim↔truth pair)

### Step 0 — Case file (Moderator)
Not an LLM step. The app displays:
- truth
- claim
- quick metadata (row id, dataset)

### Step 1 — Opening statements
- **Advocate**: 3–5 bullet reasons the claim is faithful; must cite exact phrases from truth.
- **Skeptic**: 3–5 bullet reasons it is mutated; must identify the *minimum* difference that changes meaning.

### Step 2 — Fact‑checking checklist
**Fact‑Checker** extracts from both texts:
- Numbers & units (counts, percentages)
- Dates / time windows
- Locations / entities
- Quantifiers ("more than", "under", "less than")
- Causality or correlation language

Then it outputs:
- **Match / mismatch** for each dimension
- Severity (minor vs critical)

### Step 3 — Rebuttal round(s)
Configurable (0–2).

- Advocate responds to the Skeptic + Fact‑Checker mismatches.
- Skeptic responds to Advocate defenses + Fact‑Checker matches.

### Step 4 — Verdict
The **Judge** sees the full transcript and outputs:

```json
{
  "verdict": "FAITHFUL | PARTIALLY_FAITHFUL | MUTATED",
  "confidence": 0.0,
  "rationale": ["..."],
  "critical_differences": ["..."],
  "what_would_make_it_faithful": ["..."],
  "one_sentence_summary": "..."
}
```

## Why this works for the Nova pandemic cases
Pandemic claims often mutate via:

- **Rounding/threshold language** ("under 650k" vs "more than 645k")
- **Time anchoring** ("before March 26" vs "as of March 25")
- **Geography/entity swaps** (e.g., the wrong state/country/government)
- **Scope changes** (countries vs countries+territories)
- **Omitting qualifiers** ("tested" vs "showing symptoms")

The agents are tuned to search specifically for these mutation patterns.
