"""Координатор: агенты источников, проверка и составление выжимки."""

import logging

import dailymed_agent
import ema_agent
from excerpt_agent import prepare_sections
from validator import validate_item

logger = logging.getLogger("archiv_tracker.pipeline")
AGENTS = {"DailyMed": dailymed_agent, "EMA": ema_agent}


def search_sources(term, sources, limit, start, end):
    """Опрашивать выбранные источники отдельно, сохраняя ошибки каждого."""
    results = {}
    for name in sources:
        results[name] = {"items": [], "error": None}
        try:
            items = AGENTS[name].fetch([term], rows=limit, date_from=start, date_to=end)
            for item in items:
                if not validate_item(item, [term]):
                    continue
                if name == "DailyMed":
                    try:
                        item["sections"] = dailymed_agent.fetch_label_sections(item["identifier"])
                        if not item["sections"]:
                            item["summary_error"] = "Ключевые разделы в инструкции не найдены. Откройте первоисточник."
                    except Exception:
                        logger.exception("Не удалось получить инструкцию DailyMed")
                        item["summary_error"] = "Не удалось загрузить инструкцию DailyMed. Откройте первоисточник."
                else:
                    try:
                        risk = ema_agent.fetch_risk_section(item["url"])
                        if risk:
                            item["sections"].append(risk)
                        else:
                            item["risk_notice"] = "Раздел рисков на странице EPAR не найден. Проверьте полную информацию в источнике."
                    except Exception:
                        logger.exception("Не удалось загрузить раздел рисков EMA")
                        item["risk_notice"] = "Не удалось загрузить раздел рисков EMA. Проверьте полную информацию в источнике."
                if item.get("sections"):
                    item["sections"] = prepare_sections(item["sections"])
                results[name]["items"].append(item)
        except Exception as exc:
            logger.exception("Ошибка источника %s", name)
            results[name]["error"] = str(exc)
    return results
