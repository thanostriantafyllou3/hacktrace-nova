#!/usr/bin/env python

from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
import sys

# Make `src/` importable without requiring an editable install.
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nova_debate.data import (
    default_pandemic_five,
    load_nova_csv,
    rows_from_df,
    select_pandemic_rows,
)
from nova_debate.orchestrator import run_debate_collect


async def main_async(args: argparse.Namespace) -> None:
    df = load_nova_csv(args.data)

    rows_to_run = []
    if args.row is not None:
        if args.row not in df.index:
            raise SystemExit(f"Row {args.row} not found. Valid indices: {list(df.index)}")
        r = df.loc[args.row]
        rows_to_run = [
            {
                "row_id": int(args.row),
                "claim": str(r["claim"]),
                "truth": str(r["truth"]),
            }
        ]
    elif args.pandemic:
        pandemic_df = select_pandemic_rows(df)
        preferred = default_pandemic_five(df)
        if len(preferred) >= min(5, args.limit):
            chosen = preferred[: args.limit]
        else:
            chosen = rows_from_df(pandemic_df.head(args.limit))
        rows_to_run = [r.__dict__ for r in chosen]

    results = []
    for row in rows_to_run:
        res = await run_debate_collect(
            row_id=row["row_id"],
            claim=row["claim"],
            truth=row["truth"],
            model=args.model,
            temperature=args.temperature,
            rebuttal_rounds=args.rebuttals,
            max_tokens=args.max_tokens,
        )
        results.append(res.model_dump())

        verdict = res.verdict
        print("\n" + "=" * 80)
        if verdict is not None:
            print(
                f"Row {res.row_id} | Verdict: {verdict.verdict} | Confidence: {verdict.confidence:.2f}\n{verdict.one_sentence_summary}"
            )
        else:
            print(f"Row {res.row_id} | (no verdict)")

    if args.out:
        out_path = pathlib.Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nWrote: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Nova multi-agent debate from the command line")
    parser.add_argument(
        "--data",
        default=str(pathlib.Path(__file__).resolve().parents[1] / "data" / "nova.csv"),
    )
    parser.add_argument("--model", default=os.getenv("NOVA_MODEL", "gpt-4o-mini"))
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--rebuttals", type=int, default=1)
    parser.add_argument("--max_tokens", type=int, default=None)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--row", type=int, help="Run a single row by index")
    group.add_argument("--pandemic", action="store_true", help="Run pandemic-filtered rows")

    parser.add_argument("--limit", type=int, default=5, help="When using --pandemic, how many rows to run")
    parser.add_argument("--out", type=str, default=None, help="Optional path to write JSON results")

    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
