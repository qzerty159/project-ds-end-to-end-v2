"""Controlled, sequential LLM enrichment for web-researched leads."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.scraping.llm_scraper import extract_basic_info, llm_enrich_lead, scrape_raw_text


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value)) or not str(value).strip()


def enrich_with_llm(df: pd.DataFrame, *, max_rows: int | None = None) -> pd.DataFrame:
    """Fill only blank fields from LLM output, preserving imported CRM data.

    The function runs sequentially to bound request rate and cost. ``max_rows``
    is useful for a deliberate pilot on a large CSV.
    """
    if max_rows is not None and max_rows < 1:
        raise ValueError("max_rows doit être positif lorsqu'il est renseigné.")

    enriched = df.copy()
    processed = 0
    for index, row in enriched.iterrows():
        website = row.get("website")
        if _missing(website):
            continue
        if max_rows is not None and processed >= max_rows:
            break

        raw_text = scrape_raw_text(str(website))
        if not raw_text:
            continue
        try:
            values = llm_enrich_lead(raw_text, extract_basic_info(raw_text), row.to_dict())
        except (RuntimeError, ValueError):
            # Surface API/configuration errors only if no row was processed;
            # otherwise retain useful partial enrichment and move on.
            if processed == 0:
                raise
            continue

        for key, value in values.items():
            if key not in enriched:
                enriched[key] = ""
            if _missing(enriched.at[index, key]):
                enriched.at[index, key] = value
        processed += 1
    return enriched
