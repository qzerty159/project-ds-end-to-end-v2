"""Small, robust EDA summaries used by both the UI and consultant."""

from __future__ import annotations

import pandas as pd


def basic_stats(df: pd.DataFrame) -> dict[str, float | int]:
    """Return aggregate metrics without leaking entire free-text columns."""
    if df.empty:
        return {"total_leads": 0, "avg_compatibility": 0.0, "high_value_ratio": 0.0, "contactable_ratio": 0.0}
    return {
        "total_leads": int(len(df)),
        "avg_compatibility": round(float(df["compatibility_score"].mean()), 2),
        "high_value_ratio": float(df["high_value_flag"].mean()),
        "contactable_ratio": float(df["has_contact_info"].mean()),
    }


def _performance_by(df: pd.DataFrame, column: str) -> pd.DataFrame:
    values = df.copy()
    values[column] = values[column].replace("", "Non renseigné").fillna("Non renseigné")
    grouped = values.groupby(column, dropna=False).agg(
        leads=("name", "size"),
        avg_score=("compatibility_score", "mean"),
        high_value_ratio=("high_value_flag", "mean"),
    )
    return grouped.reset_index().sort_values(["avg_score", "leads"], ascending=[False, False], ignore_index=True)


def industry_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Summarise lead quality by industry, preferring a cleaned export field."""
    cleaned_industry = df.get("industry_clean")
    group_column = "industry_clean" if cleaned_industry is not None and cleaned_industry.fillna("").astype(str).str.strip().ne("").any() else "industry"
    performance = _performance_by(df, group_column)
    return performance.rename(columns={group_column: "industry"})


def source_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Summarise lead quality by acquisition source."""
    return _performance_by(df, "source")
