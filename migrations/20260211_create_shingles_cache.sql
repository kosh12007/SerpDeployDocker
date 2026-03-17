-- Миграция: создание таблицы кеша шинглов
CREATE TABLE IF NOT EXISTS shingles_cache (
    shingle_hash VARCHAR(40) PRIMARY KEY,
    found_urls JSON,
    is_unique BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_last_updated (last_updated)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
