-- Миграция: Добавление настройки режима сэмплирования шинглов
-- Дата: 12.02.2026

INSERT IGNORE INTO settings (name, value, description, category) 
VALUES (
    'UNIQUENESS_SAMPLING_MODE', 
    'deterministic', 
    'Метод выбора шинглов для API (deterministic - по хэшу, sequential - каждый N-й)', 
    'Uniqueness'
);
