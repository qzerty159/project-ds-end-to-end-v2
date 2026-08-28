"""Transparent, deterministic compatibility scoring.

The score is a prioritisation aid, not a prediction of conversion.  Keeping the
rules here makes every assigned point auditable and lets the application work
without an API key.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

_HIGH_VALUE_INDUSTRY_TERMS = (
    "consult",
    "conseil",
    "coaching",
    "software",
    "saas",
    "informat",
    "communication",
    "marketing",
    "publicit",
    "digital",
    "professional, scientific",
    "b2b",
)
_DECISION_MAKER_TERMS = (
    "ceo",
    "chief executive",
    "founder",
    "fondateur",
    "fondatrice",
    "owner",
    "propriétaire",
    "director",
    "directeur",
    "directrice",
    "dirigeant",
    "head",
    "manager",
    "gérant",
)
_PERSONAL_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "yahoo.com",
    "icloud.com",
    "proton.me",
    "protonmail.com",
}


def _text(row: Mapping[str, Any] | pd.Series, field: str) -> str:
    """Return a normalized string for an optional lead field."""
    value = row.get(field, "")
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def score_lead(row: Mapping[str, Any] | pd.Series) -> dict[str, float]:
    """Calculate the score components for one lead.

    Components add up to 100: industry fit (25), decision-maker seniority (20),
    professional contactability (15), LinkedIn (10), website (10), data
    completeness (10), and useful context in notes (10).
    """
    industry = _text(row, "industry").casefold()
    title = _text(row, "contact_title").casefold()
    email = (_text(row, "contact_email") or _text(row, "contact_email_personal")).casefold()
    website = _text(row, "website")
    linkedin = _text(row, "contact_linkedin_url").casefold()
    notes = _text(row, "notes")
    contact_name = _text(row, "contact_full_name")
    source = _text(row, "source")

    industry_score = 25.0 if any(term in industry for term in _HIGH_VALUE_INDUSTRY_TERMS) else (10.0 if industry else 0.0)
    title_score = 20.0 if any(term in title for term in _DECISION_MAKER_TERMS) else (5.0 if title else 0.0)

    email_score = 0.0
    if "@" in email and "." in email.rsplit("@", 1)[-1]:
        domain = email.rsplit("@", 1)[-1]
        email_score = 15.0 if domain not in _PERSONAL_EMAIL_DOMAINS else 8.0

    linkedin_score = 10.0 if "linkedin.com" in linkedin else 0.0
    website_score = 10.0 if website.startswith(("http://", "https://")) else 0.0
    completeness_score = min(10.0, 2.5 * sum(bool(value) for value in (contact_name, source, website, email)))
    notes_length = len(notes)
    notes_score = 10.0 if notes_length >= 150 else (6.0 if notes_length >= 50 else (2.0 if notes_length >= 15 else 0.0))

    components = {
        "industry_score": industry_score,
        "title_score": title_score,
        "email_score": email_score,
        "linkedin_score": linkedin_score,
        "website_score": website_score,
        "completeness_score": completeness_score,
        "notes_score": notes_score,
    }
    components["rule_score"] = round(min(100.0, sum(components.values())), 2)
    return components


def compute_rule_based_score(row: Mapping[str, Any] | pd.Series) -> float:
    """Return only the auditable 0--100 deterministic score."""
    return score_lead(row)["rule_score"]
