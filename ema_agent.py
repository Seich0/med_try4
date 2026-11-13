"""Агент-источник EMA: страницы EPAR со ссылками на SmPC."""

import html
import logging
import re
from datetime import date, datetime
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from utils import resolve_date_range
from validator import _find_topic

logger = logging.getLogger("archiv_tracker.ema")
SOURCE_ID = "ema"
SOURCE_NAME = "EMA (EPAR / SmPC)"
DATA_URL = "https://www.ema.europa.eu/en/media/67423"


def _clean_text(value: str) -> str:
    """Очистить HTML-разметку внутри полей официальной выгрузки."""
    text = html.unescape(value or "")
    if re.search(r"</?[A-Za-z][^>]*>", text):
        text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    return text.strip()


def fetch_risk_section(url: str) -> Optional[Dict]:
    """Вернуть раздел рисков из обзора EPAR, если он есть на странице."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    for block in soup.select(".accordion-item"):
        heading = block.find(["h2", "h3", "h4"])
        body = block.select_one(".ema-faq__body")
        if not heading or not body:
            continue
        heading_text = heading.get_text(" ", strip=True).lower()
        if heading_text.startswith("what ") and "risks" in heading_text:
            text = body.get_text(" ", strip=True)
            if text:
                label = "Польза и риски" if "benefits" in heading_text else "Риски"
                return {"title": f"{label} (обзор EMA)", "text": text}
    return None


def fetch(topics: List[str], rows: int = 20, date_from: Optional[date] = None,
          date_to: Optional[date] = None) -> List[Dict]:
    """Искать в выгрузке страниц препаратов EMA по дате обновления."""
    date_from, date_to = resolve_date_range(date_from=date_from, date_to=date_to)
    resp = requests.get(DATA_URL, timeout=60)
    resp.raise_for_status()
    items = []
    for doc in resp.json().get("data", []):
        try:
            updated = datetime.strptime(doc.get("last_updated_date", ""), "%d/%m/%Y").date()
        except ValueError:
            continue
        url = doc.get("medicine_url", "")
        if not (date_from <= updated <= date_to and url and doc.get("category") == "Human"):
            continue
        title = doc.get("name_of_medicine") or "(без названия)"
        fields = [("Действующее вещество", "active_substance"),
                  ("Терапевтическая область", "therapeutic_area_mesh"),
                  ("Показания и применение", "therapeutic_indication")]
        sections = [{"title": label, "text": _clean_text(str(doc.get(key) or ""))}
                    for label, key in fields if doc.get(key)]
        abstract = " ".join(section["text"] for section in sections)
        if not _find_topic(f"{title} {abstract}", topics):
            continue
        items.append({"source": SOURCE_ID, "identifier": f"ema:{url}", "title": title,
                      "url": url, "abstract": abstract, "sections": sections,
                      "updated": updated.isoformat()})
    return sorted(items, key=lambda item: item["updated"], reverse=True)[:max(rows, 0)]
