-- Добавление настроек для проверки уникальности (длина шингла и шаг парсинга)
INSERT IGNORE INTO settings (name, value, description) VALUES
('UNIQUENESS_SHINGLE_LENGTH', '3', 'Длина шингла (количество слов) для проверки уникальности текста.'),
('UNIQUENESS_SHINGLE_STEP', '3', 'Шаг парсинга шинглов (проверять каждый N-й шингл) для ускорения проверки.');
