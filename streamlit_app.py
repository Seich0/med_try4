"""Лекарственный навигатор: интерфейс для двух медицинских источников."""

from datetime import date, timedelta
import html

import streamlit as st

from pipeline import search_sources
from excerpt_agent import group_sections

st.set_page_config(page_title="Лекарственный навигатор", page_icon="✳️", layout="wide")
st.markdown("""
<style>
  .stApp {background: #f7f7f2; color: #183d37;}
  [data-testid="stMainBlockContainer"] {max-width: 1180px; padding-top: 2.3rem; padding-bottom: 4rem;}
  header[data-testid="stHeader"] {background: #f7f7f2;}
  .eyebrow {font-size: .8rem; font-weight: 700; letter-spacing: .16em; color: #438377; text-transform: uppercase;}
  .hero-title {font-size: clamp(2.9rem, 5vw, 4.8rem); line-height: 1.03; letter-spacing: -.055em; font-weight: 750; color: #173d36; margin: .5rem 0 1rem;}
  .hero-lead {font-size: 1.1rem; line-height: 1.6; color: #5b716a; max-width: 670px; margin-bottom: 1.8rem;}
  .intro {border-bottom: 1px solid #d5e0d7; padding-bottom: 1.8rem; margin-bottom: 2rem;}
  .section-tag {font-size: .76rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: #65867a; margin-bottom: .4rem;}
  .source-block {border-top: 2px solid #a8c7b7; padding: 1rem 0 .6rem; margin-top: .7rem;}
  .source-title {font-size: 1.45rem; font-weight: 700; color: #183f37;}
  .source-desc {color: #627b71; font-size: .96rem; line-height: 1.45; margin-top: .25rem;}
  .status-line {color: #6b8178; font-size: .86rem; margin-top: .6rem;}
  div.stButton > button[kind="primaryFormSubmit"], div.stButton > button[kind="primary"] {background:#164e43; color:white; border:none; border-radius:8px; min-height:3rem;}
  div.stButton > button[kind="primaryFormSubmit"]:hover, div.stButton > button[kind="primary"]:hover {background:#267664; color:white;}
  div[data-testid="stForm"] {border: 1px solid #dbe5dc; background: #fff; border-radius: 14px; padding: 1.3rem 1.4rem;}
  div[data-testid="stExpander"] {background:#fff; border:1px solid #dfe9e0; border-radius:10px;}
  .flow {border-top: 1px solid #d5e0d7; margin-top: 3rem; padding-top: 1.4rem; color:#607b70; font-size:.9rem; line-height:1.6;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="intro"><div class="eyebrow">Открытые медицинские источники</div><div class="hero-title">Лекарственный<br>навигатор.</div><div class="hero-lead">Найдите сведения о препарате в американском DailyMed и европейском EMA. Два агента соберут материалы и покажут фрагменты первоисточников.</div></div>', unsafe_allow_html=True)

with st.form("search"):
    st.markdown('<div class="section-tag">Новый поиск</div>', unsafe_allow_html=True)
    term = st.text_input("Название препарата или действующего вещества", placeholder="Например: aspirin или rivaroxaban")
    st.caption("Используйте английское название. Результаты источников могут различаться.")
    source_col, count_col = st.columns([2, 1])
    with source_col:
        sources = st.multiselect("Источники", ["DailyMed", "EMA"], default=["DailyMed", "EMA"])
    with count_col:
        limit = st.selectbox("Записей на источник", [3, 5, 10], index=0)
    today = date.today()
    first, second = st.columns(2)
    with first:
        start = st.date_input("Период с", value=today - timedelta(days=365))
    with second:
        end = st.date_input("Период по", value=today)
    submitted = st.form_submit_button("Найти информацию", type="primary", use_container_width=True)

if submitted:
    if not term.strip():
        st.warning("Введите название препарата или действующего вещества.")
    elif not sources:
        st.warning("Выберите хотя бы один источник.")
    elif start > end:
        st.warning("Дата начала должна быть не позже даты окончания.")
    else:
        with st.spinner("Агенты ищут материалы и извлекают фрагменты…"):
            results = search_sources(term.strip(), sources, limit, start, end)
        st.session_state["search_results"] = results
        st.session_state["search_term"] = term.strip()
        st.session_state["search_dates"] = (start, end)

if "search_results" not in st.session_state:
    st.markdown('<div class="section-tag">Источники</div>', unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown('<div class="source-block"><div class="source-title">01 / DailyMed</div><div class="source-desc">Инструкции к препаратам из базы Национальной медицинской библиотеки США. Агент обращается к API по названию препарата.</div><div class="status-line">Дата отбора: публикация инструкции</div></div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="source-block"><div class="source-title">02 / EMA</div><div class="source-desc">Страницы препаратов Европейского агентства лекарственных средств. Агент ищет по официальной выгрузке EMA.</div><div class="status-line">Дата отбора: обновление страницы</div></div>', unsafe_allow_html=True)
else:
    query = st.session_state["search_term"]
    first_day, last_day = st.session_state["search_dates"]
    st.markdown('<div class="section-tag">Результаты поиска</div>', unsafe_allow_html=True)
    st.subheader(f"Материалы по запросу «{query}»")
    st.caption(f"Период: {first_day:%d.%m.%Y} — {last_day:%d.%m.%Y}")
    for source, result in st.session_state["search_results"].items():
        st.markdown(f'<div class="source-block"><div class="source-title">{html.escape(source)}</div></div>', unsafe_allow_html=True)
        if result["error"]:
            st.error(f"Не удалось получить данные: {result['error']}")
        elif not result["items"]:
            st.info("Совпадений за выбранный период нет. Попробуйте изменить название или расширить период.")
        else:
            st.caption(f"Найдено записей: {len(result['items'])}")
            for item in result["items"]:
                with st.expander(item["title"]):
                    day = item.get("published") or item.get("updated")
                    if day:
                        st.caption(("Опубликовано: " if item.get("published") else "Обновлено: ") + day)
                    st.markdown(f"[Открыть первоисточник]({item['url']})")
                    st.caption("Фрагменты на английском могут быть сокращены. Отсутствие фрагмента не означает отсутствие противопоказаний или рисков; полная информация — в источнике.")
                    if item.get("summary_error"):
                        st.warning(item["summary_error"])
                    if item.get("risk_notice"):
                        st.caption(item["risk_notice"])
                    for title, sections in group_sections(item.get("sections", [])).items():
                        if source == "EMA" and title == "Противопоказания":
                            continue
                        st.markdown(f"**{title}**")
                        if not sections:
                            st.caption("Отдельный фрагмент не найден. Откройте полную информацию в источнике.")
                        for section in sections:
                            if section["title"] != title:
                                st.caption(section["title"])
                            st.write(section["text"])
        if source == "EMA":
            st.caption("Ссылка ведёт на страницу EPAR. На ней доступны документы о препарате, включая SmPC. PDF SmPC не анализируется.")

st.markdown('<div class="flow"><b>Как взаимодействуют агенты</b><br>Координатор запускает агенты DailyMed и EMA. Валидатор проверяет найденные записи, затем агент подготовки фрагментов сокращает длинные разделы для показа.<br>Фрагменты не заменяют полную инструкцию; подробности и все предупреждения находятся в первоисточнике.</div>', unsafe_allow_html=True)
