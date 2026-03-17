-- Миграция: Добавление колонки зарезервированных лимитов в таблицу задач уникальности
-- Дата: 10.02.2026

ALTER TABLE uniqueness_tasks ADD COLUMN reserved_limits INT DEFAULT 0 AFTER source_text;
