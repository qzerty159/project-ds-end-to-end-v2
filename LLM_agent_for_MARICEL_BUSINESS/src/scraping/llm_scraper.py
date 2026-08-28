"""Optional LLM enrichment for already-consented public website text."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Mapping

from dotenv import load_dotenv

from src.scraping.scraper import safe_get, smart_soup

load_dotenv()

_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_NAME_PATTERN = re.compile(r"\b([A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'’-]+(?:\s+[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'’-]+)+)\b")
_ALLOWED_FIELDS = {
    "contact_full_name",
    "contact_title",
    "industry",
    "notes",
    "contact_email_personal",
    "contact_linkedin_url",
}


def scrape_raw_text(url: str) -> str:
    """Return bounded public page text, using the same URL safety policy as scraping."""
    html = safe_get(url)
    return smart_soup(html).get_text(" ", strip=True)[:4_000] if html else ""


def extract_basic_info(text: str) -> dict[str, list[str]]:
    """Perform simple local extraction before any LLM request."""
    emails = sorted(set(_EMAIL_PATTERN.findall(text)), key=str.casefold)[:3]
    names = list(dict.fromkeys(_NAME_PATTERN.findall(text)))[:3]
    titles = sorted(set(re.findall(r"\b(CEO|Founder|Manager|Director|Head|Lead)\b", text, flags=re.I)), key=str.casefold)
    return {"emails": emails, "names": names, "titles": titles[:3]}


def _get_client():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY est requis pour l'enrichissement LLM.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Le paquet `openai` est requis pour l'enrichissement LLM.") from exc
    return OpenAI(api_key=key)


def _parse_json(text: str) -> dict[str, str]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("La réponse LLM n'est pas un objet JSON.")
    return {
        field: str(value).strip()
        for field, value in payload.items()
        if field in _ALLOWED_FIELDS and value is not None and str(value).strip()
    }


def llm_enrich_lead(
    raw_text: str,
    basic_info: Mapping[str, list[str]],
    existing_row: Mapping[str, Any],
    *,
    client=None,
    model: str | None = None,
) -> dict[str, str]:
    """Infer only explicitly requested fields and return validated JSON content."""
    if not raw_text.strip():
        return {}
    client = client or _get_client()
    selected_model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    prompt = f"""You enrich a business lead from a public company webpage.
Use only information contained in the page or supplied row. Never invent an
email address, LinkedIn URL, person, or factual claim. For unknown values use an
empty string. Return exactly a JSON object with these keys: contact_full_name,
contact_title, industry, notes, contact_email_personal, contact_linkedin_url.

Page text: {raw_text[:4000]}
Local extractions: {dict(basic_info)}
Existing row: {dict(existing_row)}
"""
    response = client.responses.create(model=selected_model, input=prompt)
    return _parse_json(response.output_text)
