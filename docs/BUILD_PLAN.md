# Build Plan — FactTrace Agentic Jury

## Current status

| Phase | Status   | Notes |
|-------|----------|-------|
| 1. Setup | ✅ Done | Config, data loader, project structure |
| 2. Schemas | 🔲 Todo | Pydantic models |
| 3. Parser | 🔲 Todo | Fact Frame extraction |
| 4. Jury agents | 🔲 Todo | Round 0 votes |
| 5. Debate | 🔲 Todo | Round 1 orchestration |
| 6. Revote + Foreperson | 🔲 Todo | Round 2 + verdict |
| 7. Pipeline | 🔲 Todo | Wire in main.py |

---

## Phase 1: Setup ✅

- [x] `config.yaml` with data, agents, rubric, models
- [x] `config/loader.py` — YAML loader
- [x] `data/loader.py` — CSV loader with `pair_ids` filter
- [x] `main.py` — loads config + pairs
- [x] Dirs: `schemas/`, `agents/`, `workflow/`, `prompts/`

---

## Phase 2: Schemas 🔲

Create Pydantic models for structured LLM output.

| File | Model(s) | Purpose |
|------|----------|---------|
| `schemas/fact_frame.py` | `Quantity`, `Scope`, `FactFrame` | Parser output |
| `schemas/agent_output.py` | `KeyEvidence`, `AgentOutput` | Jury agent output |
| `schemas/verdict.py` | `Verdict` | Foreperson output |

**Fields to include** (see README):

- **FactFrame:** entities, quantities, scope, modality, relationship_type, caveats
- **AgentOutput:** verdict (Faithful|Mutated), confidence, key_evidence, reasoning
- **Verdict:** verdict, 5 rubric axes (bool), failed_axes, reasoning, optional dissent_note, minimal_edit

---

## Phase 3: Parser 🔲

**Goal:** Extract a Fact Frame from (claim, truth).

| Task | Where | Notes |
|------|-------|-------|
| System prompt | `prompts/parser.txt` | Instruct LLM to extract entities, quantities, scope, modality, relationship_type, caveats |
| Chat model | `agents/parser.py` | LangChain ChatOpenAI + `with_structured_output(FactFrame)` |
| Config | `models.parser` | Use model ID from config |

**LangChain pattern:**
```python
llm = ChatOpenAI(model=config["models"]["parser"])
structured_llm = llm.with_structured_output(FactFrame)
```

---

## Phase 4: Jury agents (Round 0) 🔲

**Goal:** Each agent independently votes Faithful or Mutated.

| Agent | Role | Focus |
|-------|------|-------|
| literal | Literal Fact-Checker | Numbers, dates, explicit statements |
| context | Context Guardian | Nuance, caveats, qualifiers |
| steelman | Steelman Advocate | Best interpretation of claim |
| sceptic | Sceptic | Worst interpretation, exaggeration |

| Task | Where | Notes |
|------|-------|-------|
| Prompts | `prompts/jury_*.txt` or one template | Role + Fact Frame + claim + truth |
| Agent builder | `agents/jury.py` | One function to build agent by name; use `with_structured_output(AgentOutput)` |
| Round 0 runner | `workflow/round0.py` | For each agent, invoke with claim, truth, fact_frame → list of AgentOutput |

---

## Phase 5: Debate (Round 1) 🔲

**Goal:** If verdict is split, run rule-based debate (constructives, rebuttals).

| Task | Where | Notes |
|------|-------|-------|
| Debate logic | `workflow/debate.py` | Side A (Faithful), Side B (Mutated); constructives then rebuttals; max `debate.max_rounds` |
| Speaker selection | — | E.g. alternate sides, or by disagreement strength |
| Output | — | Transcript + updated stances (agents can change vote) |

**Rule-based (no Moderator):** Two sides, fixed turns. Optional: LLM checker for "no new arguments" early stop.

---

## Phase 6: Revote + Foreperson 🔲

**Goal:** Round 2 revote, then Foreperson applies binary rubric.

| Task | Where | Notes |
|------|-------|-------|
| Round 2 | `workflow/round2.py` | Same as Round 0 but agents see debate transcript |
| Foreperson prompt | `prompts/foreperson.txt` | Rubric axes as Yes/No questions; output Verdict |
| Foreperson agent | `agents/foreperson.py` | `with_structured_output(Verdict)` |
| Dissent | — | If ≥ `dissent_threshold` on minority → `dissent_note` |

**Rubric aggregation:** All Yes → Faithful; ≥1 No → Mutated; tie/ambiguous → Ambiguous.

---

## Phase 7: Pipeline 🔲

**Goal:** End-to-end flow in `main.py`.

```
load_config → load_pairs
  for each pair:
    parse(claim, truth) → fact_frame
    round0(fact_frame, claim, truth) → votes
    if split: debate → transcript
    round2(..., transcript) → revotes
    foreperson(revotes, rubric) → verdict
    save/print verdict
```

| Task | Notes |
|------|-------|
| Wire in main.py | Loop over pairs, call workflow steps |
| Output format | Print to stdout or write JSON |
| Env | `OPENAI_API_KEY` from env (LangChain default) |

---

## Quick reference

- **Data path:** `data/csvs/Nova.csv` (update config if different)
- **pair_ids:** `[0, 5, 9, 10, 13]` in config
- **Models:** All `gpt-4o-mini` by default; set `OPENAI_API_KEY`

---

## Changelog

| Date | Change |
|------|--------|
| — | Initial plan |
