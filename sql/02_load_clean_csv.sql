-- Запускати через psql із кореня репозиторію після 01_schema_and_views.sql.
-- Потрібна порожня база: дані не видаляються та не перезаписуються.
\set ON_ERROR_STOP on
BEGIN;
\copy device (device_id, device_name) FROM 'SkillForge_clean/device.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy country (country_id, country_code) FROM 'SkillForge_clean/country.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy experiment_group (group_id, group_label) FROM 'SkillForge_clean/experiment_group.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy users (user_id, device_id, country_id, group_id, days_on_product) FROM 'SkillForge_clean/users.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\copy daily (user_id, date, converted) FROM 'SkillForge_clean/daily.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
COMMIT;
