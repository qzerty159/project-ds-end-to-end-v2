"""CSV validation, normalisation, and deterministic lead enrichment."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, TextIO

import pandas as pd

from src.scoring.rule_based_score import score_lead

DEFAULT_COLUMNS = (
    "name",
    "website",
    "contact_email",
    "industry",
    "notes",
    "source",
    "contact_full_name",
    "contact_title",
    "contact_email_personal",
    "contact_linkedin_url",
)
_COLUMN_ALIASES = {
    "company": "name",
    "company_name": "name",
    "lead_name": "name",
    "note": "notes",
    "comment": "notes",
    "linkedin": "contact_linkedin_url",
    "linkedin_url": "contact_linkedin_url",
    "email": "contact_email",
    "email_address": "contact_email",
    "title": "contact_title",
}


def load_leads_data(file: str | Path | BinaryIO | TextIO) -> pd.DataFrame:
    """Load a UTF-8 CSV and normalize its headers.

    A lead name is the only mandatory input. Other scoring fields are optional;
    missing ones are created empty so a partial export can still be analysed.
    """
    try:
        dataframe = pd.read_csv(file, low_memory=False)
    except (OSError, UnicodeDecodeError, pd.errors.ParserError) as exc:
        raise ValueError(f"Impossible de lire le CSV : {exc}") from exc
    return normalize_leads_schema(dataframe)


def normalize_leads_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize common column aliases and make text fields safe to use."""
    if df.empty:
        raise ValueError("Le CSV ne contient aucune ligne.")

    normalized = df.copy()
    normalized.columns = [str(column).strip().casefold().replace(" ", "_") for column in normalized.columns]
    normalized = normalized.rename(columns=_COLUMN_ALIASES)

    # If an export supplied both `note` and `notes`, retain the first non-empty
    # value instead of creating ambiguous duplicate headers.
    if normalized.columns.duplicated().any():
        merged: dict[str, pd.Series] = {}
        for column in dict.fromkeys(normalized.columns):
            same_name = normalized.loc[:, normalized.columns == column]
            merged[column] = same_name.bfill(axis=1).iloc[:, 0]
        normalized = pd.DataFrame(merged, index=normalized.index)

    if "name" not in normalized.columns:
        raise ValueError("Le CSV doit contenir une colonne `name` (ou `company`).")

    for column in DEFAULT_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = ""
        normalized[column] = normalized[column].fillna("").astype(str).str.strip()

    normalized["name"] = normalized["name"].replace("", "Lead sans nom")
    return normalized


def enrich_leads(
    df: pd.DataFrame,
    *,
    high_value_threshold: float = 70.0,
    preserve_existing_score: bool = False,
) -> pd.DataFrame:
    """Add score components and prioritisation flags to a lead DataFrame.

    By default the score is recalculated from the visible rules. Set
    ``preserve_existing_score`` for an already validated CRM score; the computed
    rule score remains available for comparison in ``rule_score``.
    """
    if not 0 <= high_value_threshold <= 100:
        raise ValueError("Le seuil high-value doit être compris entre 0 et 100.")

    enriched = normalize_leads_schema(df)
    component_frame = pd.DataFrame(enriched.apply(score_lead, axis=1).tolist(), index=enriched.index)
    enriched = pd.concat([enriched, component_frame], axis=1)

    raw_existing_score = enriched.get("compatibility_score", pd.Series(pd.NA, index=enriched.index))
    existing_score = pd.to_numeric(raw_existing_score, errors="coerce").clip(0, 100)
    use_existing = preserve_existing_score & existing_score.notna()
    enriched["compatibility_score"] = enriched["rule_score"].where(~use_existing, existing_score).round(2)
    enriched["compatibility_score_source"] = "rule_based"
    enriched.loc[use_existing, "compatibility_score_source"] = "existing_input"
    enriched["compatibility_score_norm"] = enriched["compatibility_score"] / 100.0
    enriched["high_value_flag"] = (enriched["compatibility_score"] >= high_value_threshold).astype(int)
    enriched["has_contact_info"] = (
        enriched[["contact_email", "contact_email_personal", "contact_linkedin_url"]].ne("").any(axis=1)
    )
    return enriched
 
