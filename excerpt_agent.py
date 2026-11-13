"""Агент подготовки коротких фрагментов из разделов источников."""

GROUPS = {
    "Показания и применение": {"Показания и применение"},
    "Противопоказания": {"Противопоказания"},
    "Предупреждения и риски": {
        "Особое предупреждение", "Предупреждения", "Предупреждения и меры предосторожности",
        "Риски (обзор EMA)", "Польза и риски (обзор EMA)",
    },
}


def prepare_sections(sections, limit=1000):
    """Сократить длинные разделы, сохраняя их названия и исходный текст."""
    result = []
    for section in sections:
        text = section["text"]
        if len(text) > limit:
            text = text[:limit].rsplit(" ", 1)[0] + "…"
        result.append({"title": section["title"], "text": text})
    return result


def group_sections(sections):
    """Общие рубрики с сохранением исходных названий фрагментов."""
    return {group: [s for s in sections if s["title"] in titles]
            for group, titles in GROUPS.items()}
