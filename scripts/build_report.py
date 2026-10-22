"""Export saved results to one portable HTML; never run analytical code.

Usage: python scripts/build_report.py --eda-notebook /path/to/original_eda.ipynb
The EDA notebook and datasets are local inputs outside the public repository.
"""
import argparse
import base64
import copy
import html
import json
import re
from pathlib import Path

import nbformat
from bs4 import BeautifulSoup
from nbconvert import HTMLExporter

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/djon-sql/skillforge-ab-test-analysis'
TABLEAU = 'https://public.tableau.com/app/profile/djon.fa/viz/SkillForce/01AB-'


def md(source):
    return nbformat.v4.new_markdown_cell(source)


def prepare(source, prefix):
    """Preserve all code; omit individual records and EDA identifier dumps."""
    result = []
    omitted = 0
    for original in source.cells:
        cell = copy.deepcopy(original)
        if cell.cell_type == 'markdown':
            if cell.source.startswith('# '):
                continue
            lines = cell.source.splitlines()
            if lines and re.match(r'^#{2,3} ', lines[0]):
                match = re.match(r'^(#{2,3})\s+(?:(\d+(?:\.\d+)*)\.?\s+)?(.+)$', lines[0])
                marks, number, label = match.groups()
                if label == 'Опис проєкту':
                    cell.source = '\n'.join(lines[1:]).lstrip()
                    result.append(cell)
                    continue
                if number is None:
                    number = '4.1'
                elif prefix == '1' and number == '4.1':
                    number = '4.2'
                lines[0] = '#' + marks + ' ' + f'{prefix}.{number}. {label}'
                cell.source = '\n'.join(lines)
        elif cell.cell_type == 'code':
            allowed = []
            for output in cell.get('outputs', []):
                data = output.get('data', {})
                text = str(output.get('text', '')) + str(data.get('text/plain', ''))
                rendered = str(data.get('text/html', ''))
                if 'user_id' in text + rendered:
                    omitted += 1
                    continue
                allowed.append(output)
            cell.outputs = allowed
        result.append(cell)
    assert [c.source for c in source.cells if c.cell_type == 'code'] == [c.source for c in result if c.cell_type == 'code']
    return result, omitted


def toc(soup):
    aliases = {'1':'eda', '2':'sql', '3':'ab-test', '4':'tableau', '5':'metric-definitions', '6':'methodology-notes',
        '3.4':'conversion', '3.5':'significance', '3.6':'confidence-interval', '3.7':'sensitivity',
        '3.8':'segments', '3.9':'weekly-trends', '3.10':'conclusions', '3.10.4':'recommendations'}
    chapters = []
    items = []
    for heading in soup.select('main h2, main h3, main h4'):
        for anchor in heading.select('.anchor-link'):
            anchor.decompose()
        label = heading.get_text(' ', strip=True)
        match = re.match(r'^(\d+(?:\.\d+)*)\.', label)
        if not match:
            continue
        number = match.group(1)
        identifier = aliases.get(number, 'section-' + number.replace('.', '-'))
        heading['id'] = identifier
        item = {'level':int(heading.name[1]), 'id':identifier, 'label':label}
        items.append(item)
        if heading.name == 'h2':
            chapters.append({'main':item, 'children':[]})
        else:
            chapters[-1]['children'].append(item)
        back = soup.new_tag('p', attrs={'class':'sf-section-return'})
        link = soup.new_tag('a', href='#report-contents')
        link.string = '↑ До змісту'
        back.append(link)
        heading.insert_after(back)
    cards = []
    for chapter in chapters:
        item = chapter['main']
        card = f'<div class="sf-toc-item"><a class="sf-toc-main" href="#{item["id"]}">{html.escape(item["label"])}</a>'
        if chapter['children']:
            card += f'<details><summary>Підрозділи ({len(chapter["children"])})</summary><ul>'
            for child in chapter['children']:
                cls = ' class="sf-toc-sub"' if child['level'] == 4 else ''
                card += f'<li{cls}><a href="#{child["id"]}">{html.escape(child["label"])}</a></li>'
            card += '</ul></details>'
        cards.append(card + '</div>')
    return ''.join(cards), items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--eda-notebook', type=Path, required=True)
    args = parser.parse_args()
    eda_source = nbformat.read(args.eda_notebook, as_version=4)
    ab_source = nbformat.read(ROOT/'SkillForge_Kupriyanov_ab_test_analysis.ipynb', as_version=4)
    nbformat.validate(eda_source)
    nbformat.validate(ab_source)
    eda, omitted_eda = prepare(eda_source, '1')
    ab, omitted_ab = prepare(ab_source, '3')
    sql = (ROOT/'sql/01_schema_and_views.sql').read_text()
    split_daily = sql.index('CREATE OR REPLACE VIEW v_daily_agg')
    split_user = sql.index('CREATE OR REPLACE VIEW v_user_conversion')
    chunks = [sql[:split_daily], sql[split_daily:split_user], sql[split_user:]]
    cells = [md('## 1. Дослідження та очищення даних\n\nПочаткові пояснення, авторський код і збережені узагальнені результати EDA. Індивідуальні записи та службові виводи з ідентифікаторами не включено до публічної версії.')]
    cells += eda
    cells += [md('## 2. PostgreSQL: таблиці та аналітичні view\n\nАвторський SQL з останнього наданого файлу `SkillForge_sql(1).sql`. Структуру, умови й формули збережено без змін. [Відкрити SQL на GitHub](' + REPO + '/blob/main/sql/01_schema_and_views.sql).')]
    for title, code in zip(['2.1. Структура таблиць', '2.2. Щоденна агрегація — v_daily_agg', '2.3. Підсумкова конверсія користувача — v_user_conversion'], chunks):
        cells.append(md('### ' + title + '\n\n```sql\n' + code.rstrip() + '\n```'))
    cells += [md('**Зміст view.** `v_daily_agg` агрегує записи за датою та групою. Його `conver_rate` — частка позитивних статусів серед відомих за день. `v_user_conversion` формує один підсумковий статус на користувача: конверсія має пріоритет; без неї невідомий статус залишається `NULL`. Користувачі без щоденних записів також отримують `NULL`. Користувачі без визначеної групи не входять до обох view через `JOIN experiment_group`.'),
        md('## 3. Аналіз результатів A/B-тесту\n\nАвторські розрахунки та збережені результати. Основна одиниця аналізу — користувач із визначеною групою та відомим підсумковим статусом конверсії.')]
    cells += ab
    cells += [md('## 4. Інтерактивні дашборди Tableau\n\n[Відкрити Tableau Public →](' + TABLEAU + ')\n\nДва дашборди: **«Результати A/B-тесту»** та **«Аналіз сегментів»**. Порівняння A/B, динаміка та зрізи за країнами й пристроями. Знімок нижче доступний без інтернету; інтерактивний дашборд відкривається за посиланням.'),
        md('<img class="sf-dashboard" src="data:image/png;base64,' + base64.b64encode((ROOT/'assets/04_tableau_overview.png').read_bytes()).decode() + '" alt="Дашборд Tableau SkillForge: конверсія A/B, приріст і щоденна динаміка">'),
        md('''## 5. Визначення показників

| Показник | Визначення |
|---|---|
| Основна конверсія | Користувачі зі статусом 1 / користувачі зі статусом 0 або 1. Основна вибірка: 9 716. |
| Абсолютний приріст | Конверсія B мінус конверсія A, у процентних пунктах. |
| Відносний приріст | (Конверсія B / конверсія A − 1) × 100%. |
| Довірчий інтервал | Двосторонній 95% інтервал різниці B − A, метод Newcombe. |
| Крайні сценарії | Невідомим статусам надаються протилежні значення в A/B. Знаменник: усі 9 946 учасників із визначеною групою. |
| Тижнева активність | Середня щоденна кількість користувачів із записами daily за періоди 7, 7 і 6 днів. |
| Щоденний conver_rate | Частка позитивних статусів серед відомих щоденних записів; це інша метрика, ніж основна конверсія за весь тест. |'''),
        md('''## 6. Обмеження аналізу

- Навчальні змодельовані дані, варіант 42; період — 20 днів.
- У 54 користувачів немає визначеної групи: вони не входять до A/B-порівняння.
- Невідомі підсумкові статуси: A — 144, B — 86. Основний аналіз виключає їх, сценарії враховують крайні можливі значення.
- У EDA 229 невідомих статусів стосуються користувачів із наявними daily та пропусками, включно з 5 без групи. У підсумковому view до 224 із визначеною групою додаються 6 без daily — разом 230.
- Відмінності між сегментами та схожість трендів описові: окремих тестів взаємодії чи рівності трендів не проводили.
- У третьому періоді немає четверга; склад днів тижня може частково пояснювати нижче середнє.
- Утримання, скасування підписок і дохід не розраховані. Ці дані не визначають довгостроковий або фінансовий ефект.

**Про вебверсію.** HTML містить збережені результати та відкривається локально без бази даних. Кнопка «Показати код» відкриває авторський Python. Код Python та формули не змінено; вебверсія не запускає їх повторно. Для повторного виконання потрібні вихідні дані та PostgreSQL.''')]
    combined = nbformat.v4.new_notebook(cells=cells, metadata=ab_source.metadata)
    for i, cell in enumerate(combined.cells):
        cell.id = f'sf-cell-{i:03}'
    exporter = HTMLExporter(template_name='lab', exclude_input_prompt=True, exclude_output_prompt=True)
    rendered, _ = exporter.from_notebook_node(combined)
    soup = BeautifulSoup(rendered, 'html.parser')
    soup.html['lang'] = 'uk'
    soup.title.string = 'SkillForge — повний аналіз A/B-тесту | Дмитро Купріянов'
    for tag in soup.select('script,link[rel="stylesheet"]'):
        tag.decompose()
    style = soup.new_tag('style')
    style.string = (ROOT/'assets/report.css').read_text()
    soup.head.append(style)
    contents, items = toc(soup)
    header = f'''<nav class="sf-toolbar" aria-label="Швидка навігація звітом"><a href="#report-summary">Огляд</a><a href="#report-contents">Зміст</a><a href="#eda">Дані</a><a href="#sql">SQL</a><a href="#ab-test">A/B-тест</a><a href="#conclusions">Висновки</a><a href="#tableau">Tableau</a><button type="button" id="sf-code-toggle" aria-pressed="false" hidden>Показати код</button></nav>
<header class="sf-shell" id="report-summary"><div class="sf-eyebrow">Python · PostgreSQL · Tableau · Варіант 42</div><h1>SkillForge — A/B-тест нового онбордингу</h1>
<p class="sf-lead">Чи підвищує «Миттєве занурення» конверсію в преміум-підписку? Повний аналіз: від перевірки й очищення даних до статистичного тесту, сегментів та бізнес-рекомендацій.</p><p class="sf-meta">Автор: Дмитро Купріянов · Період експерименту: 01–20.08.2025 · Навчальні змодельовані дані</p>
<div class="sf-actions"><a href="#report-contents">Перейти до аналізу ↓</a><a href="{REPO}">Репозиторій GitHub ↗</a><a href="{TABLEAU}">Tableau Public ↗</a><a href="{REPO}/blob/main/SkillForge_Kupriyanov_ab_test_analysis.ipynb">Jupyter Notebook ↗</a></div>
<div class="sf-metrics" aria-label="Основні результати"><div class="sf-metric"><strong>43,13%</strong><span>конверсія A — контроль</span></div><div class="sf-metric"><strong>64,73%</strong><span>конверсія B — новий онбординг</span></div><div class="sf-metric"><strong>+21,60 п.п.</strong><span>абсолютний приріст B − A</span></div><div class="sf-metric"><strong>+50,08%</strong><span>відносний приріст до A</span></div></div>
<section class="sf-insights" aria-label="Головне з аналізу"><h2>Головне з аналізу</h2><ul><li><strong>B має вищу конверсію в преміум-підписку.</strong> Різниця статистично значуща й зберігається в крайніх сценаріях невідомих статусів.</li><li>Основний аналіз: <strong>9 716 користувачів</strong> із відомим статусом; конверсії A — 2 097 із 4 862, B — 3 142 із 4 854.</li><li>95% довірчий інтервал різниці: <strong>[+19,65; +23,52] п.п.</strong>; одностороннє p ≈ 1,69 × 10⁻¹⁰¹.</li><li><strong>Рекомендація:</strong> розглядати B для поетапного впровадження після перевірки трекінгу та з контролем додаткових бізнес-метрик.</li></ul><p class="sf-note">Далі наведено початкові пояснення, авторський код, збережені узагальнені таблиці та графіки. Код можна показати кнопкою вгорі.</p></section>
<nav class="sf-toc" id="report-contents" aria-labelledby="sf-contents-title"><h2 id="sf-contents-title">Зміст звіту</h2><p class="sf-toc-intro">Натисніть назву розділу. У пункті «Підрозділи» є переходи до кожного етапу аналізу.</p><div class="sf-toc-grid">{contents}</div></nav></header>'''
    soup.body.insert(0, BeautifulSoup(header, 'html.parser'))
    footer = f'<footer class="sf-shell sf-footer"><p>Дмитро Купріянов · Junior Data Analyst · <a href="{REPO}">GitHub</a> · <a href="{TABLEAU}">Tableau Public</a></p><p>Один HTML-файл зі збереженими результатами. Графіки, стилі та навігація працюють без завантаження додаткових файлів.</p></footer><a class="sf-fab" href="#report-contents">↑ Зміст</a>'
    soup.body.append(BeautifulSoup(footer, 'html.parser'))
    script = soup.new_tag('script')
    script.string = (ROOT/'assets/report.js').read_text()
    soup.body.append(script)
    for image in soup.select('.jp-RenderedImage img'):
        image['alt'] = image.get('alt') or 'Графік з авторського аналізу SkillForge'
    ids = [x['id'] for x in soup.select('[id]')]
    assert len(ids) == len(set(ids)), 'Duplicate HTML anchors'
    assert all(a['href'][1:] in ids for a in soup.select('a[href^="#"]'))
    assert not soup.select('script[src],link[rel="stylesheet"]')
    assert all(x.get('src', '').startswith('data:') for x in soup.select('img'))
    (ROOT/'index.html').write_text(str(soup), encoding='utf-8')
    aliases = {'3.4':'conversion', '3.5':'significance', '3.6':'confidence-interval', '3.7':'sensitivity', '3.8':'segments', '3.9':'weekly-trends', '3.10':'conclusions'}
    for filename, target, prefix in [('eda.html','eda','1'), ('ab-test.html','ab-test','3')]:
        forward = f'''<!doctype html><html lang="uk"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SkillForge — вебзвіт</title><meta http-equiv="refresh" content="0;url=index.html#{target}"><p><a href="index.html#{target}">Відкрити повний вебзвіт SkillForge →</a></p><script>const aliases={json.dumps(aliases)};const m=location.hash.match(/^#section-(.+)$/);let id='{target}';if(m){{const number='{prefix}.'+m[1].replaceAll('-','.');id=aliases[number]||'section-'+number.replaceAll('.','-');}}location.replace('index.html#'+id);</script></html>'''
        (ROOT/filename).write_text(forward)
    print(json.dumps({'file':'index.html', 'navigation_targets':len(items), 'eda_code_cells':sum(c.cell_type=='code' for c in eda), 'ab_code_cells':sum(c.cell_type=='code' for c in ab), 'eda_identifier_outputs_omitted':omitted_eda, 'ab_outputs_omitted':omitted_ab, 'bytes':(ROOT/'index.html').stat().st_size}, ensure_ascii=False))


if __name__ == '__main__':
    main()
