-- Миграция: Добавление исходного текста в таблицу задач уникальности
-- Дата: 10.02.2026

ALTER TABLE uniqueness_tasks ADD COLUMN source_text LONGTEXT AFTER user_id;
