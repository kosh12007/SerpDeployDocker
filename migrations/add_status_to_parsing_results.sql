-- Добавляем поле status в таблицу parsing_position_results
-- Это поле будет отслеживать состояние результата парсинга: успех, ошибка или в ожидании
ALTER TABLE parsing_position_results
ADD COLUMN status ENUM('success', 'error', 'pending') NOT NULL DEFAULT 'pending' AFTER top_10_urls;

-- Обновляем статус для уже существующих записей
-- Если поле top_10_urls равно NULL, значит, парсинг не удался
UPDATE parsing_position_results
SET status = 'error'
WHERE top_10_urls IS NULL OR top_10_urls = '[]';

-- Для остальных записей, если top_10_urls не пустой, ставим статус 'success'
UPDATE parsing_position_results
SET status = 'success'
WHERE status = 'pending' AND top_10_urls IS NOT NULL AND top_10_urls != '[]';

-- Добавляем индекс для ускорения поиска по статусу
CREATE INDEX idx_parsing_position_results_status ON parsing_position_results (status);

-- Добавляем индекс для ускорения поиска по статусу и дате
CREATE INDEX idx_parsing_position_results_status_date ON parsing_position_results (status, date);

-- Добавляем индекс для ускорения поиска по статусу, дате и query_id
CREATE INDEX idx_parsing_position_results_status_date_query ON parsing_position_results (status, date, query_id);