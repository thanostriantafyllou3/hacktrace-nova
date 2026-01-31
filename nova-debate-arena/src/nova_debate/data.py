from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Iterable, List, Optional

import pandas as pd


DATASET_COLUMNS = ("claim", "truth")


@dataclass(frozen=True)
class DatasetRow:
    """A single claim↔truth pair."""

    row_id: int
    claim: str
    truth: str


def load_nova_csv(path: str | pathlib.Path) -> pd.DataFrame:
    """Load the Nova CSV (expects columns: 'claim', 'truth')."""
    path = pathlib.Path(path)
    df = pd.read_csv(path)
    missing = [c for c in DATASET_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Nova CSV missing expected columns {missing}. Found columns: {list(df.columns)}"
        )
    # Keep original index for stable referencing
    df = df.copy()
    return df


PANDEMIC_KEYWORDS = [
    "covid",
    "coronavirus",
    "pandemic",
    "sars",
    "lockdown",
    "cases",
    "deaths",
    "tested",
]


def select_pandemic_rows(
    df: pd.DataFrame, keywords: Optional[Iterable[str]] = None
) -> pd.DataFrame:
    """Return subset of rows that look pandemic/COVID-related."""
    keywords = list(keywords) if keywords is not None else PANDEMIC_KEYWORDS
    pattern = "|".join([k for k in keywords if k])
    mask = df["claim"].astype(str).str.contains(pattern, case=False, na=False) | df[
        "truth"
    ].astype(str).str.contains(pattern, case=False, na=False)
    return df[mask].copy()


def rows_from_df(df: pd.DataFrame) -> List[DatasetRow]:
    rows: List[DatasetRow] = []
    for idx, r in df.iterrows():
        rows.append(DatasetRow(row_id=int(idx), claim=str(r["claim"]), truth=str(r["truth"])))
    return rows


def default_pandemic_five(df: pd.DataFrame) -> List[DatasetRow]:
    """Pick 5 pandemic-relevant rows (stable defaults for Nova.csv).

    Nova.csv shipped for the hackathon contains 6 pandemic-like rows with indices:
    1, 4, 5, 10, 11, 12. We pick 5 diverse ones and skip 10 (very similar to 1/4).

    If these indices aren't present, falls back to the first 5 pandemic rows.
    """

    pandemic = select_pandemic_rows(df)

    preferred = [1, 4, 5, 11, 12]
    if all(i in pandemic.index for i in preferred):
        return rows_from_df(df.loc[preferred])

    # Fallback: first 5 pandemic rows
    return rows_from_df(pandemic.head(5))
