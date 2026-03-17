-- Добавляем колонку spent_limits в таблицу parsing_sessions
ALTER TABLE parsing_sessions
ADD COLUMN spent_limits INTEGER NOT NULL DEFAULT 0;