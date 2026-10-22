"""Export saved SkillForge notebook outputs; do not execute analytical code."""

from pathlib import Path
import base64
import html
import re

import nbformat
from bs4 import BeautifulSoup
from nbconvert import HTMLExporter
from pygments.formatters import HtmlFormatter

ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/djon-sql/skillforge-ab-test-analysis"
TABLEAU = "https://public.tableau.com/app/profile/djon.fa/viz/SkillForce/01AB-"


def esc(value):
    return html.escape(str(value), quote=True)


def toc_html(items):
    return "".join(
        f'<a class="toc-link level-{level}" href="#{esc(identifier)}">{esc(label)}</a>'
        for level, identifier, label in items
    )


def shell(title, subtitle, current, body, toc, source=None):
    links = [("index.html", "Огляд", "overview"), ("eda.html", "EDA та очищення", "eda"),
             ("ab-test.html", "A/B-аналіз", "ab")]
    nav = "".join(
        f'<a href="{url}"' + (' aria-current="page"' if key == current else '') + f'>{label}</a>'
        for url, label, key in links
    )
    code_tools = '' if source is None else (
        '<button type="button" id="code-toggle" aria-pressed="false">Показати весь код</button>'
        f'<a href="{esc(source)}" download>Завантажити .ipynb ↓</a>'
    )
    return f'''<!doctype html>
<html lang="uk"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{esc(subtitle)}"><meta name="color-scheme" content="light">
<title>{esc(title)} · SkillForge</title><link rel="stylesheet" href="assets/site.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23162d46'/%3E%3Ctext x='32' y='43' text-anchor='middle' fill='white' font-family='sans-serif' font-size='36'%3ES%3C/text%3E%3C/svg%3E">
</head><body id="top"><a class="skip-link" href="#main">Перейти до вмісту</a>
<header class="topbar"><a class="brand" href="index.html"><span class="brand-mark">S</span>SkillForge<span class="brand-sub">A/B-тест</span></a>
<nav class="page-nav" aria-label="Сторінки проєкту">{nav}<a href="{TABLEAU}" target="_blank" rel="noopener noreferrer">Tableau ↗</a></nav>
<button type="button" id="menu-toggle" aria-controls="sidebar" aria-expanded="false">Зміст ☰</button></header>
<div class="page-layout"><aside id="sidebar" class="sidebar" aria-label="Навігація розділами">
<p class="sidebar-eyebrow">НА ЦІЙ СТОРІНЦІ</p><nav>{toc_html(toc)}</nav>
<div class="sidebar-bottom"><a href="{REPO}" target="_blank" rel="noopener noreferrer">Репозиторій GitHub ↗</a><a href="#top">На початок ↑</a></div></aside>
<main id="main" tabindex="-1"><div class="page-heading"><p class="eyebrow">НАВЧАЛЬНИЙ ПРОЄКТ · ВАРІАНТ 42</p><h1>{esc(title)}</h1><p class="page-subtitle">{esc(subtitle)}</p>
<div class="meta-row"><span>Дмитро Купріянов</span><span>01–20.08.2025</span><span>Python · PostgreSQL · Tableau</span></div></div>
<div class="page-tools">{code_tools}<a href="index.html#materials">Усі матеріали →</a></div>
{body}
<footer><p>Дмитро Купріянов · Junior Data Analyst</p><p>Навчальні змодельовані дані. Публічна версія містить код, графіки й узагальнені результати; індивідуальні рядки не розповсюджуються.</p>
<div><a href="#top">На початок ↑</a><a href="{REPO}">GitHub</a><a href="{TABLEAU}">Tableau Public</a></div></footer></main></div>
<script src="assets/site.js" defer></script></body></html>'''


def export_notebook(name, filename, title, subtitle, current):
    nb = nbformat.read(ROOT / name, as_version=4)
    nbformat.validate(nb)
    exporter = HTMLExporter(template_name="basic")
    exporter.exclude_input_prompt = True
    exporter.exclude_output_prompt = True
    fragment, _ = exporter.from_notebook_node(nb)
    soup = BeautifulSoup(fragment, "html.parser")
    for heading in soup.select("h1"):
        heading.decompose()  # The notebook title is repeated in the page heading.
    items, seen = [], set()
    for i, heading in enumerate(soup.select("h2, h3")):
        for link in heading.select(".anchor-link"):
            link.decompose()
        label = heading.get_text(" ", strip=True)
        match = re.match(r"(\d+(?:\.\d+)*)\.", label)
        identifier = "section-" + match.group(1).replace(".", "-") if match else f"context-{i + 1}"
        if identifier in seen:
            identifier += f"-{i + 1}"
        seen.add(identifier)
        heading["id"] = identifier
        heading["tabindex"] = "-1"
        items.append((int(heading.name[1]), identifier, label))
    for i, cell in enumerate(soup.select(".code_cell"), 1):
        input_area = cell.select_one(".input")
        if input_area:
            details = soup.new_tag("details", attrs={"class": "code-disclosure"})
            summary = soup.new_tag("summary")
            summary.string = f"Код Python · блок {i}"
            details.append(summary)
            input_area.wrap(details)
    for image in soup.select("img"):
        image["alt"] = image.get("alt") or "Графік зі збережених результатів ноутбука SkillForge"
        image["loading"] = "eager"
    for wrapper in soup.select(".output_html, .output_text, .output_stream"):
        wrapper["class"] = wrapper.get("class", []) + ["scroll-output"]
    for table in soup.select(".text_cell_render > table"):
        wrapper = soup.new_tag("div", attrs={"class": "table-wrap"})
        table.wrap(wrapper)
    note = ('<div class="reading-note"><strong>Як читати:</strong> результати й пояснення відкриті; '
            'код можна розгорнути під кожним блоком або однією кнопкою. Зміст ліворуч веде до розділів. '
            'Широкі таблиці можна прокручувати горизонтально. '
            'Для повторного обчислення потрібне середовище з README.</div>')
    body = note + '<article class="notebook">' + str(soup) + '</article>'
    (ROOT / filename).write_text(shell(title, subtitle, current, body, items, name), encoding="utf-8")
    return nb


OVERVIEW = '''
<article class="overview">
<section id="decision" tabindex="-1" class="decision-card"><span class="pill">ВИСНОВОК ЕКСПЕРИМЕНТУ</span>
<h2>Новий онбординг B має вищу конверсію</h2><p>64,73% у B проти 43,13% у A. Перевага зберігається навіть за найгіршого для B розподілу невідомих статусів.</p>
<p class="decision-action">Рекомендація — розглядати B для поетапного впровадження після перевірки трекінгу та з контролем бізнес-показників.</p>
<div class="button-row"><a class="button button-light" href="ab-test.html#section-10">Висновки та рекомендації →</a><a class="text-link" href="ab-test.html">Повний аналіз →</a></div></section>
<div class="kpi-grid" aria-label="Головні показники"><div class="kpi"><span>Конверсія A</span><strong class="group-a">43,13%</strong><small>Контрольна група</small></div>
<div class="kpi"><span>Конверсія B</span><strong class="group-b">64,73%</strong><small>Тестова група</small></div><div class="kpi"><span>Абсолютний приріст</span><strong>+21,60 <em>п.п.</em></strong><small>B − A</small></div><div class="kpi"><span>Відносний приріст</span><strong>+50,08%</strong><small>Порівняно з A</small></div></div>
<p class="scope-note">Конверсія — серед 9 716 користувачів із визначеною групою та відомим підсумковим статусом за весь експеримент.</p>
<section id="context" tabindex="-1"><div class="section-label">01 / КОНТЕКСТ</div><h2>Що перевіряє тест</h2><p>SkillForge — навчальна платформа. Гіпотеза: автоматичний перехід до першого інтерактивного уроку підвищує конверсію в преміум-підписку.</p>
<div class="two-column"><div class="comparison-card"><span class="group-label group-a">ГРУПА A · КОНТРОЛЬ</span><h3>Спочатку — перелік тем</h3><p>Традиційний сценарій після реєстрації.</p><strong>5 006 учасників</strong></div><div class="comparison-card"><span class="group-label group-b">ГРУПА B · ТЕСТ</span><h3>Одразу — інтерактивний урок</h3><p>Новий онбординг «Миттєве занурення».</p><strong>4 940 учасників</strong></div></div>
<p class="scope-note">Навчальні змодельовані дані, варіант 42. Період: 01–20 серпня 2025 року.</p></section>
<section id="results" tabindex="-1"><div class="section-label">02 / РЕЗУЛЬТАТ</div><h2>Перевага B підтверджена статистично</h2><figure><img src="assets/01_conversion.png" alt="Конверсія в преміум-підписку: 43,13% у A та 64,73% у B"><figcaption>Користувацька конверсія за весь експеримент. Знаменник — відомі підсумкові статуси.</figcaption></figure>
<div class="stat-strip"><div><span>Односторонній z-тест</span><strong>p &lt; 0,001</strong><small>α = 0,05</small></div><div><span>95% ДІ різниці B − A</span><strong>+19,65…+23,52 п.п.</strong><small>Двосторонній інтервал Newcombe</small></div></div>
<div class="table-wrap"><table><thead><tr><th>Вибірка</th><th>A</th><th>B</th></tr></thead><tbody><tr><td>Відомий статус</td><td>4 862</td><td>4 854</td></tr><tr><td>Підтверджена конверсія</td><td>2 097</td><td>3 142</td></tr><tr><td>Невідомий статус</td><td>144</td><td>86</td></tr></tbody></table></div>
<div class="callout"><strong>Перевірка стійкості.</strong> Крайні сценарії для невідомих статусів дають різницю від +18,84 до +23,45 п.п. Сценарії використовують усіх 9 946 учасників із визначеною групою; основна оцінка — 9 716 відомих статусів.</div><a class="section-link" href="ab-test.html#section-4">До розрахунків конверсії та приросту →</a></section>
<section id="segments" tabindex="-1"><div class="section-label">03 / СЕГМЕНТИ</div><h2>Перевага є в основних країнах і пристроях</h2><p>Для планшетів приріст становить +25,33 п.п.; для мобільних пристроїв — +21,66 п.п.; для комп’ютерів — +21,32 п.п. Серед п’яти основних країн приріст лежить від +15,64 п.п. у Франції до +24,81 п.п. у Бразилії.</p>
<div class="callout caution"><strong>Межа висновку.</strong> Це описові зрізи. Відмінності ефекту між сегментами окремо не тестувалися. Smartwatch, TV та XX мають малі вибірки; не можна на цій основі заявляти відсутність впливу.</div>
<a class="section-link" href="ab-test.html#section-8">Таблиці сегментів і висновки →</a><a class="section-link" href="https://public.tableau.com/app/profile/djon.fa/viz/SkillForce/01AB-" target="_blank" rel="noopener noreferrer">Фільтри й графіки в Tableau ↗</a></section>
<section id="trends" tabindex="-1"><div class="section-label">04 / ВИКОРИСТАННЯ ПРОДУКТУ</div><h2>Щоденні коливання A і B схожі</h2><figure><img src="assets/03_daily_usage.png" alt="Щоденна кількість користувачів із записами daily в групах A та B за 01–20 серпня 2025"><figcaption>На графіку — користувачі зі щоденними записами, а не основна конверсія.</figcaption></figure>
<p>Найнижчі значення припадають на неділі, найвищі — на четверги. Перші два періоди відносно стабільні; середнє третього нижче в обох групах.</p><p class="scope-note">Третій період містить шість днів і не має четверга. Склад днів тижня частково пояснює нижче середнє. Статистичну рівність трендів не перевіряли.</p><a class="section-link" href="ab-test.html#section-9">Тижневі графіки та пояснення →</a></section>
<section id="data" tabindex="-1"><div class="section-label">05 / ПІДГОТОВКА</div><h2>Від сирих записів до перевіреної вибірки</h2><div class="table-wrap"><table><thead><tr><th>Крок</th><th>Результат</th></tr></thead><tbody><tr><td>Початкові щоденні записи</td><td>61 002</td></tr><tr><td>Видалення 1 196 повних дублікатів</td><td>59 806</td></tr><tr><td>Видалення 60 записів поза експериментом</td><td>59 746</td></tr><tr><td>Користувачі після очищення</td><td>10 000</td></tr><tr><td>З визначеною групою A/B</td><td>9 946</td></tr></tbody></table></div>
<p>20 негативних значень days_on_product замінено на пропуски. 501 невідомий щоденний статус збережено: невідоме значення не є нулем.</p><a class="section-link" href="eda.html">Повний EDA зі збереженим кодом →</a></section>
<section id="method" tabindex="-1"><div class="section-label">06 / МЕТОДИКА</div><h2>Що означає конверсія</h2><p>Один користувач має підсумковий статус за весь період: 1 — є підтверджена конверсія; NULL — підтвердження немає, але є невідомі статуси або немає записів; 0 — усі наявні статуси відомі та нульові.</p>
<p><strong>Конверсія = кількість користувачів зі статусом 1 / кількість користувачів зі статусом 0 або 1.</strong></p><p>v_user_conversion містить один рядок на користувача; v_daily_agg — один рядок на дату та групу. Щоденна частка позитивних статусів має інший знаменник і не замінює головну метрику.</p>
<div class="callout caution"><strong>Обмеження.</strong> Навчальні дані, 20 днів спостережень, нерівномірні пропуски, малі сегменти. Дохід, утримання та скасування не розраховані — це показники для контролю майбутнього запуску.</div><a class="section-link" href="ab-test.html#section-2">Опис експерименту й гіпотези →</a></section>
<section id="materials" tabindex="-1"><div class="section-label">07 / МАТЕРІАЛИ</div><h2>Переглянути повний проєкт</h2><div class="two-column"><a class="material-card" href="eda.html"><span class="card-tag">PYTHON · PANDAS</span><h3>EDA та очищення →</h3><p>Якість даних, пропуски, дублікати, типи та підготовка CSV.</p></a><a class="material-card" href="ab-test.html"><span class="card-tag">СТАТИСТИКА · БІЗНЕС</span><h3>A/B-аналіз →</h3><p>Конверсія, значущість, інтервал, чутливість, сегменти та висновки.</p></a></div>
<a class="tableau-preview" href="https://public.tableau.com/app/profile/djon.fa/viz/SkillForce/01AB-" target="_blank" rel="noopener noreferrer"><img src="assets/04_tableau_overview.png" alt="Опублікований головний дашборд SkillForge у Tableau"><span>Відкрити інтерактивний Tableau ↗</span></a>
<div class="download-links"><a href="SkillForge_Kupriyanov_eda_cleaning.ipynb" download>EDA .ipynb ↓</a><a href="SkillForge_Kupriyanov_ab_test_analysis.ipynb" download>A/B .ipynb ↓</a><a href="https://github.com/djon-sql/skillforge-ab-test-analysis">README, дані та SQL ↗</a></div></section></article>
'''


def main():
    (ROOT / "assets").mkdir(exist_ok=True)
    ab = export_notebook("SkillForge_Kupriyanov_ab_test_analysis.ipynb", "ab-test.html",
                         "A/B-аналіз нового онбордингу", "Від гіпотези до бізнес-рекомендацій: конверсія, статистика, сегменти та тренди.", "ab")
    export_notebook("SkillForge_Kupriyanov_eda_cleaning.ipynb", "eda.html",
                    "Дослідження та очищення даних", "Перевірка якості п’яти таблиць і підготовка даних до PostgreSQL та A/B-аналізу.", "eda")
    for i, name in [(37, "01_conversion"), (66, "02_weekly_usage"), (69, "03_daily_usage")]:
        png = ab.cells[i].outputs[0].data["image/png"]
        (ROOT / "assets" / f"{name}.png").write_bytes(base64.b64decode(png))
    items = [(2, "decision", "Висновок"), (2, "context", "1. Контекст"), (2, "results", "2. Результат"),
             (2, "segments", "3. Сегменти"), (2, "trends", "4. Тижневі тренди"), (2, "data", "5. Підготовка даних"),
             (2, "method", "6. Методика"), (2, "materials", "7. Матеріали")]
    (ROOT / "index.html").write_text(shell("Чи варто впроваджувати новий онбординг?",
        "SkillForge — результати A/B-тесту та рекомендація для бізнесу.", "overview", OVERVIEW, items), encoding="utf-8")
    (ROOT / "assets" / "syntax.css").write_text(HtmlFormatter(style="friendly").get_style_defs(".highlight"), encoding="utf-8")
    print("Built index.html, eda.html, ab-test.html and notebook chart assets.")


if __name__ == "__main__":
    main()
