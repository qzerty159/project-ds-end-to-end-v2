"""Opt-in concurrent enrichment that keeps DataFrame writes on the main thread."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd

from src.scraping.scraper import scrape_linkedin, scrape_website


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value)) or not str(value).strip()


def _process_row(index: Any, row: pd.Series) -> tuple[Any, dict[str, str]]:
    """Collect enrichment data without sharing a mutable DataFrame across threads."""
    updates: dict[str, str] = {"scraped_emails": "", "scraped_names": "", "scraped_titles": ""}
    web_data: dict[str, Any] = {"scraped_emails": [], "scraped_names": []}
    linkedin_data: dict[str, Any] = {"scraped_titles": []}

    website = row.get("website")
    if not _missing(website):
        web_data = scrape_website(str(website))
        updates["scraped_emails"] = ", ".join(web_data["scraped_emails"])
        updates["scraped_names"] = ", ".join(web_data["scraped_names"])

    linkedin = row.get("contact_linkedin_url")
    if not _missing(linkedin):
        linkedin_data = scrape_linkedin(str(linkedin))
        updates["scraped_titles"] = ", ".join(linkedin_data["scraped_titles"])

    if _missing(row.get("contact_full_name")) and web_data["scraped_names"]:
        updates["contact_full_name"] = web_data["scraped_names"][0]
    if _missing(row.get("contact_email_personal")) and web_data["scraped_emails"]:
        updates["contact_email_personal"] = web_data["scraped_emails"][0]
    if _missing(row.get("contact_title")) and linkedin_data["scraped_titles"]:
        updates["contact_title"] = linkedin_data["scraped_titles"][0]
    return index, updates


def enrich_with_scraping(
    df: pd.DataFrame,
    *,
    max_workers: int = 5,
    max_rows: int | None = None,
) -> pd.DataFrame:
    """Enrich rows from public pages, preserving existing lead values.

    Failures for individual sites leave the row unchanged. This is deliberately
    opt-in at the pipeline level because URLs can contain personal data and web
    sites' terms of use must be respected.
    """
    if max_workers < 1:
        raise ValueError("max_workers doit être supérieur ou égal à 1.")
    if max_rows is not None and max_rows < 1:
        raise ValueError("max_rows doit être positif lorsqu'il est renseigné.")
    enriched = df.copy()
    for column in ("scraped_emails", "scraped_names", "scraped_titles"):
        if column not in enriched:
            enriched[column] = ""

    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for row_number, (index, row) in enumerate(enriched.iterrows()):
            if max_rows is not None and row_number >= max_rows:
                break
            futures.append(executor.submit(_process_row, index, row.copy()))
        for future in as_completed(futures):
            try:
                index, updates = future.result()
            except Exception:
                # A single inaccessible site must not prevent CSV analysis.
                continue
            for column, value in updates.items():
                if value:
                    enriched.at[index, column] = value
    return enriched
