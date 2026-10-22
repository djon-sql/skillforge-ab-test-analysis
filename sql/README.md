# PostgreSQL

У поточній публічній версії таблиці `users.csv` і `daily.csv` не розповсюджуються. Команди імпорту нижче потребують повного навчального набору даних.

`01_schema_and_views.sql` — авторський SQL створення таблиць та двох view; його аналітичну логіку збережено.

`02_load_clean_csv.sql` — допоміжний імпорт через `psql`, доданий для відтворення роботи. Запускати з кореня репозиторію після створення таблиць у порожній базі.

## Імпорт через DBeaver

1. Створити базу `skillforge` та виконати `01_schema_and_views.sql`.
2. Імпортувати CSV з `SkillForge_clean` у порядку: **device → country → experiment_group → users → daily**.
3. Формат CSV: UTF-8, роздільник — кома, перший рядок — заголовки, порожні поля — SQL NULL. Не підміняти їх нулями.
4. Очікувані кількості: device — 5; country — 6; experiment_group — 2; users — 10 000; daily — 59 746.
5. `v_user_conversion` має 9 946 рядків; `v_daily_agg` — 40. Дані для порівняння збережені в `data/views/`.

У фактичному SQL поле `daily.converted` — **INTEGER із CHECK IN (0, 1)** та дозволеним NULL. Це відповідає наданим CSV і використаним формулам SUM/COUNT.
