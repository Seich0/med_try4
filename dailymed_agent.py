"""Агент-источник инструкций DailyMed (поиск по названию препарата)."""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Dict, List, Optional

import requests

from utils import resolve_date_range

logger = logging.getLogger("archiv_tracker.dailymed")
SOURCE_ID = "dailymed"
SOURCE_NAME = "DailyMed"
API_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json"
SPL_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{}.xml"
NS = {"hl7": "urn:hl7-org:v3"}
SECTION_NAMES = {
    "34066-1": "Особое предупреждение",
    "34067-9": "Показания и применение",
    "34070-3": "Противопоказания",
    "34071-1": "Предупреждения",
    "43685-7": "Предупреждения и меры предосторожности",
}


def fetch_label_sections(identifier: str) -> List[Dict]:
    """Загрузить структурированную SPL-инструкцию и её ключевые разделы."""
    set_id = identifier.removeprefix("dailymed:")
    resp = requests.get(SPL_URL.format(set_id), timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    sections = []
    for section in root.findall(".//hl7:section", NS):
        code = section.find("hl7:code", NS)
        label = SECTION_NAMES.get(code.get("code", "")) if code is not None else None
        if not label:
            continue
        parts = []
        # Текст бывает в самом разделе и во вложенных подразделах.
        for node in [section, *section.findall(".//hl7:section", NS)]:
            title = node.find("hl7:title", NS)
            body = node.find("hl7:text", NS)
            if body is not None:
                if node is not section and title is not None:
                    parts.append(" ".join(title.itertext()))
                parts.append(" ".join(body.itertext()))
        text = re.sub(r"\s+", " ", " ".join(parts)).strip()
        if text:
            sections.append({"title": label, "text": text})
    return sections


def fetch(topics: List[str], rows: int = 20, date_from: Optional[date] = None,
          date_to: Optional[date] = None) -> List[Dict]:
    """Искать инструкции по названиям препаратов и дате публикации."""
    date_from, date_to = resolve_date_range(date_from=date_from, date_to=date_to)
    items = {}
    for topic in topics:
        page = 1
        matched = 0
        while rows > 0:
            resp = requests.get(API_URL, params={
                "drug_name": topic, "published_date": date_from.isoformat(),
                "published_date_comparison": "gte", "pagesize": 100, "page": page,
            }, timeout=30)
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            data = resp.json()
            for doc in data.get("data", []):
                try:
                    published = datetime.strptime(doc["published_date"], "%b %d, %Y").date()
                except (KeyError, ValueError):
                    continue
                if date_from <= published <= date_to and doc.get("setid"):
                    ident = doc["setid"]
                    items[ident] = {
                        "source": SOURCE_ID, "identifier": f"dailymed:{ident}",
                        "title": doc.get("title") or "(без названия)",
                        "url": f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={ident}",
                        "abstract": "", "published": published.isoformat(),
                    }
                    matched += 1
            next_page = data.get("metadata", {}).get("next_page")
            if matched >= rows or next_page in (None, "", "null"):
                break
            page += 1
    return sorted(items.values(), key=lambda item: item["published"], reverse=True)[:max(rows, 0)]
