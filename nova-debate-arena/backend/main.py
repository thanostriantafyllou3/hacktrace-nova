from __future__ import annotations

import os
import pathlib
import sys
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Ensure `src/` is importable without requiring pip install -e .
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nova_debate.data import default_pandemic_five, load_nova_csv, select_pandemic_rows
from nova_debate.orchestrator import debate_events

load_dotenv(override=False)

APP_TITLE = "Nova Cartoon Debate Arena"

DATA_PATH = ROOT / "data" / "nova.csv"
FRONTEND_DIR = ROOT / "frontend"

# Load dataset once at startup
DF = load_nova_csv(DATA_PATH)
DEFAULT_IDS = {r.row_id for r in default_pandemic_five(DF)}
PANDEMIC_DF = select_pandemic_rows(DF)

app = FastAPI(title=APP_TITLE)

# Static assets
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "title": APP_TITLE,
        "rows_total": int(len(DF)),
        "pandemic_rows": int(len(PANDEMIC_DF)),
        "default_focus": sorted(DEFAULT_IDS),
        "default_model": os.getenv("NOVA_MODEL", "gpt-4o-mini"),
    }


@app.get("/api/cases")
def list_cases() -> Dict[str, Any]:
    """Return the pandemic/COVID-related subset for the UI."""

    cases = []
    for idx, row in PANDEMIC_DF.iterrows():
        cases.append(
            {
                "row_id": int(idx),
                "claim": str(row["claim"]),
                "truth": str(row["truth"]),
                "is_default": int(idx) in DEFAULT_IDS,
            }
        )

    return {"cases": cases, "default_ids": sorted(DEFAULT_IDS)}


@app.websocket("/ws/debate")
async def ws_debate(ws: WebSocket):
    """Run a debate and stream events to the browser."""

    await ws.accept()

    try:
        payload = await ws.receive_json()

        if payload.get("action") != "start":
            await ws.send_json({"type": "error", "message": "Expected {action: 'start'}"})
            await ws.close()
            return

        row_id = int(payload.get("row_id"))
        if row_id not in DF.index:
            await ws.send_json(
                {
                    "type": "error",
                    "message": f"Row {row_id} not found. Valid indices: {list(DF.index)}",
                }
            )
            await ws.close()
            return

        row = DF.loc[row_id]
        truth = str(row["truth"])
        claim = str(payload.get("claim_override") or row["claim"])

        model = str(payload.get("model") or os.getenv("NOVA_MODEL", "gpt-4o-mini"))
        temperature = float(payload.get("temperature", 0.2))
        rebuttals = int(payload.get("rebuttal_rounds", 1))

        max_tokens: Optional[int] = payload.get("max_tokens", None)
        if max_tokens is not None:
            try:
                max_tokens = int(max_tokens)
            except Exception:
                max_tokens = None

        await ws.send_json(
            {
                "type": "meta",
                "model": model,
                "temperature": temperature,
                "rebuttal_rounds": rebuttals,
                "max_tokens": max_tokens,
            }
        )

        async for event in debate_events(
            row_id=row_id,
            claim=claim,
            truth=truth,
            model=model,
            temperature=temperature,
            rebuttal_rounds=rebuttals,
            max_tokens=max_tokens,
        ):
            await ws.send_json(event)

    except WebSocketDisconnect:
        # Client disconnected; nothing to do.
        return
    except Exception as ex:
        try:
            await ws.send_json({"type": "error", "message": str(ex)})
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass
