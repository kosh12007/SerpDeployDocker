-- Добавление настройки срока жизни кеша проверенных шинглов (в днях)
INSERT IGNORE INTO settings (name, value, description, category) 
VALUES ('UNIQUENESS_CACHE_TTL', '14', 'Срок жизни кеша результатов проверки уникальности в днях (по умолчанию 14)', 'Uniqueness');
