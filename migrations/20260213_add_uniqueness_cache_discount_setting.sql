-- Добавление настройки коэффициента скидки для кешированных шинглов
INSERT IGNORE INTO settings (name, value, description, category) 
VALUES ('UNIQUENESS_CACHE_DISCOUNT', '50', 'Коэффициент скидки для шинглов из кеша в процентах (0 - бесплатно, 100 - полная стоимость)', 'Uniqueness');
