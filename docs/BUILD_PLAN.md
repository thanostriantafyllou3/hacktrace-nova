# Build Plan — FactTrace Agentic Jury

## Current status: ✅ Complete

| Phase | Status | Notes |
|-------|--------|-------|
| 1. Setup | ✅ Done | Config, data loader, project structure |
| 2. Schemas | ✅ Done | Fact, FactFrame, Evidence, JuryOutput, AxisResult, Verdict |
| 3. Parser | ✅ Done | Fact Frame extraction via structured output |
| 4. Jury agents | ✅ Done | Round 0 + Revote via `run_vote`, role-based prompts |
| 5. Debate | ✅ Done | Multi-round (Mutated ↔ Faithful); stops at max_rounds, concession, or no new args |
| 6. Revote + Foreperson | ✅ Done | Config-driven rubric, axis_results |
| 7. Pipeline | ✅ Done | LangGraph: parse → initial_vote → [debate] → revote → foreperson |

---

## Phase 1: Setup ✅

- [x] `config.yaml` with data, agents, rubric, models, interactive flag
- [x] `config/loader.py` — YAML loader
- [x] `data/loader.py` — CSV loader with `pair_ids` filter, returns `{id, claim, truth}`
- [x] `main.py` — loads config, pairs, runs pipeline (interactive or quiet)
- [x] Dirs: `schemas/`, `agents/`, `workflow/`, `prompts/`, `config/`, `data/`

---

## Phase 2: Schemas ✅

| File | Model(s) | Purpose |
|------|----------|---------|
| `schemas/fact_frame.py` | `Fact`, `FactFrame` | Parser output: flexible facts with category, claim_says, truth_says, note |
| `schemas/jury_output.py` | `Evidence`, `JuryOutput` | Agent output: verdict, confidence, evidence (Fact+issue), reasoning |
| `schemas/verdict.py` | `AxisResult`, `Verdict` | Foreperson: config-driven rubric axes, summary, minimal_edit, dissent_note |

---

## Phase 3: Parser ✅

- [x] `prompts/parser.txt` — instructs LLM to extract facts
- [x] `agents/parser.py` — ChatOpenAI + `with_structured_output(FactFrame)`
- [x] Config: `models.parser`

---

## Phase 4: Jury agents ✅

- [x] `prompts/jury/vote_template.txt` — shared template with `{role_instruction}`, `{claim}`, `{truth}`, `{fact_frame}`, `{debate_section}`
- [x] `prompts/jury/{literal,context,steelman,sceptic}.txt` — role instructions
- [x] `agents/jury.py` — `run_jury(agent_name, claim, truth, fact_frame, config, transcript=None)`
- [x] `workflow/vote.py` — `run_vote()` via RunnableParallel, `is_split()` helper

---

## Phase 5: Debate ✅

- [x] `prompts/jury/debate_template.txt` — agents present arguments, respond to transcript
- [x] `prompts/jury/debate_status_check.txt` — LLM checks concession / no new arguments
- [x] `schemas/debate_status.py` — `DebateStatus` (conceded, no_new_arguments)
- [x] `workflow/debate.py` — `run_debate()`: multi-round Mutated ↔ Faithful; speakers rotate
- [x] Early termination: max rounds, concession, or no new arguments (LLM checker)

---

## Phase 6: Revote + Foreperson ✅

- [x] `run_vote()` reused with optional `transcript` for revote
- [x] `prompts/foreperson.txt` — rubric questions from config
- [x] `agents/foreperson.py` — `run_foreperson()` with structured Verdict
- [x] `axis_results` per rubric axis; `dissent_note` when minority ≥ dissent_threshold

---

## Phase 7: Pipeline ✅

- [x] LangGraph `StateGraph(JuryState)` in `workflow/graph.py`
- [x] Nodes: parse, initial_vote, debate, revote, foreperson
- [x] Conditional edge: split → debate, unanimous → revote
- [x] `run_pipeline()` — invoke (quiet)
- [x] `run_pipeline_interactive()` — stream + print each step
- [x] `main.py` — loops pairs, uses config `interactive` flag
- [x] `.env` with `OPENAI_API_KEY`, `python-dotenv` for loading

---

## How to run

```bash
uv sync
cp .env.example .env   # set OPENAI_API_KEY
uv run python src/main.py
```

Config: `config.yaml` (data source, pair_ids, agents, rubric, models, interactive).

---

## Changelog

| Date | Change |
|------|--------|
| — | Initial plan |
| — | All phases complete; LangGraph pipeline; interactive CLI |
| — | Debate: multi-round with early stop (max_rounds, concession, no_new_arguments) |
