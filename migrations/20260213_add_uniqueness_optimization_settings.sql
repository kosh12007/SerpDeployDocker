-- Миграция: Настройки оптимизации хранения результатов уникальности
INSERT IGNORE INTO settings (name, value, description, category) VALUES
('UNIQUENESS_MIN_MATCH_PERCENT', '2', 'Минимальный процент совпадений для сайта, чтобы он попал в отчет (0-100).', 'Uniqueness'),
('UNIQUENESS_MAX_MATCH_URLS', '100', 'Максимальное количество сайтов, сохраняемых в результате одной проверки.', 'Uniqueness');
