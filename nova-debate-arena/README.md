# Nova Cartoon Debate Arena (LangChain + FastAPI + Realtime UI)

This is the same **Nova multi-agent jury** (Advocate ↔ Skeptic ↔ Fact-Checker → Judge), but with a **nicer, live “cartoon-ish” realtime web UI**.

- ✅ Uses **LangChain** for all LLM calls (streaming enabled)
- ✅ Uses **FastAPI WebSocket** to stream debate events
- ✅ Browser UI renders a **live debate arena** with speech bubbles (no gradients; flat cartoon style)
- ✅ Focuses on **5 pandemic/COVID-related** claim↔truth pairs from `data/nova.csv` (but you can run any pandemic row)

---

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

pip install -r requirements.txt
cp .env.example .env  # set OPENAI_API_KEY

uvicorn backend.main:app --reload --port 8000
```

Then open:

```text
http://localhost:8000
```

---

## How the debate works

See: `docs/PLAN.md`

**Verdicts**:
- `FAITHFUL`
- `PARTIALLY_FAITHFUL`
- `MUTATED`

**Hard rule**: agents must use **only** the provided Truth text (no external knowledge).

---

## CLI (optional)

Run one row:

```bash
python scripts/run_cli.py --row 4
```

Run the default pandemic 5:

```bash
python scripts/run_cli.py --pandemic --limit 5 --out outputs/results.json
```

---

## Project structure

- `backend/main.py` – FastAPI server + WebSocket streaming
- `frontend/` – static UI (HTML/CSS/JS)
- `src/nova_debate/` – LangChain agents + orchestrator
- `data/nova.csv` – dataset

---

## Notes

- If you deploy behind HTTPS, the UI will automatically switch to `wss://`.
- Streaming is token-by-token (as supported by the chosen model/provider).
