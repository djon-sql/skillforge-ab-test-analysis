--Ствоення таблиць та структури таблиць 



-- Довідник типів пристроїв користувачів
CREATE TABLE  device (

device_id INTEGER PRIMARY KEY,
device_name TEXT UNIQUE NOT NULL

);

-- Довідник країн користувачів
CREATE TABLE country (

country_id INTEGER PRIMARY KEY,
country_code TEXT UNIQUE NOT NULL

);

-- Довідник груп A/B тесту:
-- A — контрольна група, B — тестова група
CREATE TABLE  experiment_group ( 

group_id INTEGER PRIMARY KEY,
group_label TEXT UNIQUE NOT NULL CHECK (group_label IN ('A', 'B'))

);


-- Основна таблиця користувачів.
-- Зберігає пристрій, країну, групу A/B тесту та кількість днів користування продуктом.
CREATE TABLE users (

user_id INTEGER PRIMARY KEY,
device_id INTEGER,
country_id INTEGER,
group_id INTEGER,
days_on_product INTEGER CHECK (days_on_product >= 0),

FOREIGN KEY (device_id) REFERENCES device(device_id),
FOREIGN KEY (country_id) REFERENCES country(country_id),
FOREIGN KEY (group_id) REFERENCES experiment_group(group_id)

);


-- Щоденні записи активності користувачів у межах A/B тесту.
-- converted: 1 — конверсія відбулася, 0 — не відбулася, NULL — статус конверсії невідомий.
CREATE TABLE daily (

user_id INTEGER NOT NULL,
date DATE NOT NULL,
converted INTEGER CHECK (converted IN (0, 1)),

  PRIMARY KEY (user_id, date),
  FOREIGN KEY (user_id) REFERENCES users(user_id)

);


CREATE OR REPLACE VIEW v_daily_agg AS 
SELECT 
    d.date,
    eg.group_label,
    COUNT(*) AS cnt_users,
    SUM(d.converted) AS cnt_conversions,
    SUM(CASE WHEN d.converted IS NULL THEN 1 ELSE 0 END) AS cnt_unknown_convert,
    COUNT(d.converted) AS cnt_known,
    ROUND((SUM(d.converted) / COUNT(d.converted)::NUMERIC) * 100,2) AS conver_rate
FROM users AS u 
   JOIN daily AS d 
      ON u.user_id = d.user_id 
   JOIN experiment_group AS eg 
      ON u.group_id = eg.group_id 
GROUP BY d.date,eg.group_label;


SELECT *
FROM v_daily_agg
ORDER BY date, group_label;

--Денна агрегація показує кількість користувачів, підтверджених конверсій, невідомих статусів та conversion rate окремо для груп A і B за кожен день тесту.

CREATE OR REPLACE VIEW v_user_conversion AS
SELECT 
    u.user_id,
    eg.group_label,
    d.device_name,
    c.country_code,
    u.days_on_product,
    CASE
        WHEN SUM(CASE WHEN da.converted = 1 THEN 1 ELSE 0 END) > 0
            THEN 1
        WHEN SUM(CASE WHEN da.converted IS NULL THEN 1 ELSE 0 END) > 0
            THEN NULL
        ELSE 0
    END AS conversion_status
FROM users u
   JOIN experiment_group eg
      ON u.group_id = eg.group_id
   LEFT JOIN device d
      ON u.device_id = d.device_id
   LEFT JOIN country c
       ON u.country_id = c.country_id
   LEFT JOIN daily da
       ON u.user_id = da.user_id
GROUP BY
    u.user_id,
    eg.group_label,
    d.device_name,
    c.country_code,
    u.days_on_product;


SELECT *
FROM v_user_conversion
ORDER BY user_id;

--v_user_conversion формує один підсумковий запис на кожного користувача та визначає його статус конверсії за весь період тесту. 
--View буде використана для основного A/B аналізу та сегментації користувачів.
