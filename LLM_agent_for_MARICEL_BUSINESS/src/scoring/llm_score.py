"""Optional LLM scoring with explicit configuration and strict output parsing."""

from __future__ import annotations

import os
import re
from typing import Any, Mapping

from dotenv import load_dotenv

load_dotenv()


def _lead_value(row: Mapping[str, Any], field: str) -> str:
    value = row.get(field, "")
    return "" if value is None else str(value).strip()


def _get_client():
    """Build an OpenAI client only when an LLM feature is explicitly used."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY est requis pour utiliser le scoring LLM.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Le paquet `openai` est requis pour utiliser le scoring LLM.") from exc
    return OpenAI(api_key=api_key)


def _parse_score(value: str) -> float:
    match = re.search(r"(?<!\d)(100|[1-9]?\d)(?:\.\d+)?(?!\d)", value)
    if not match:
        raise ValueError("La réponse LLM ne contient pas de score numérique valide.")
    return max(0.0, min(float(match.group(0)), 100.0))


def compute_llm_score(row: Mapping[str, Any], *, client=None, model: str | None = None) -> float:
    """Return a 0--100 semantic score for one lead.

    This function intentionally raises configuration/API errors rather than
    silently assigning a neutral score. Callers can then disclose a partial
    analysis instead of presenting an invented result as model output.
    """
    client = client or _get_client()
    selected_model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    prompt = f"""You are qualifying a B2B lead for growth and consulting services.
Score the lead from 0 to 100 based only on the supplied data. Do not infer facts
that are not present. Return exactly one number and no explanation.

Company: {_lead_value(row, 'name')}
Industry: {_lead_value(row, 'industry')}
Contact title: {_lead_value(row, 'contact_title')}
Website: {_lead_value(row, 'website')}
Notes: {_lead_value(row, 'notes')[:1500]}
"""
    response = client.responses.create(model=selected_model, input=prompt)
    return _parse_score(response.output_text)
