"""Conservative public-web scraping used only after explicit user opt-in."""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_NAME_PATTERN = re.compile(r"\b([A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'’-]+(?:\s+[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'’-]+)+)\b")
_TITLE_PATTERN = re.compile(r"\b(CEO|Founder|Co-Founder|Manager|Director|Head|Lead|Fondateur|Fondatrice|Dirigeant|Gérant)\b", re.I)


def _is_public_url(url: str) -> bool:
    """Allow only public http(s) endpoints, preventing CSV-driven SSRF."""
    try:
        parsed = urlsplit(url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return False
        host = parsed.hostname.rstrip(".")
        if host.casefold() == "localhost":
            return False
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
        except socket.gaierror:
            return False
        if not addresses:
            return False
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if not ip.is_global:
                return False
        return True
    except (TypeError, ValueError):
        return False


def smart_soup(html: str) -> BeautifulSoup:
    """Parse XML-looking documents without warning noise."""
    return BeautifulSoup(html, "xml" if html.lstrip().startswith("<?xml") else "html.parser")


def safe_get(url: str, *, timeout: float = 10.0) -> str | None:
    """Fetch a small public HTML document without following redirects."""
    if not isinstance(url, str) or not _is_public_url(url):
        return None
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            headers={"User-Agent": "MARICELLeadResearch/1.0 (+contact@example.invalid)"},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").casefold()
            if content_type and not any(value in content_type for value in ("text/", "application/xhtml", "application/xml")):
                return None
            return response.text[:1_000_000]
    except httpx.HTTPError:
        return None


def _extract(html: str) -> tuple[list[str], list[str], str]:
    soup = smart_soup(html)
    text = soup.get_text(" ", strip=True)
    emails = sorted(set(_EMAIL_PATTERN.findall(text)), key=str.casefold)[:3]
    names = list(dict.fromkeys(_NAME_PATTERN.findall(text)))[:3]
    return emails, names, text


def scrape_website(url: str) -> dict[str, list[str] | str]:
    """Extract public emails and probable names from a company's own website."""
    html = safe_get(url)
    if not html:
        return {"scraped_emails": [], "scraped_names": [], "raw_text": ""}
    emails, names, text = _extract(html)
    return {"scraped_emails": emails, "scraped_names": names, "raw_text": text[:2_000]}


def scrape_linkedin(url: str) -> dict[str, list[str] | str]:
    """Extract title terms from a public page; no login or bypass is attempted."""
    html = safe_get(url)
    if not html:
        return {"scraped_titles": [], "raw_text": ""}
    _, _, text = _extract(html)
    titles = list(dict.fromkeys(match.group(0) for match in _TITLE_PATTERN.finditer(text)))
    return {"scraped_titles": titles[:3], "raw_text": text[:2_000]}
