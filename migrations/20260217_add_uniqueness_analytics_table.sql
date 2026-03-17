-- Миграция: Создание таблицы uniqueness_analytics для персистентной аналитики
-- Описание: Таблица хранит агрегированные данные по каждой завершённой проверке уникальности.
--           Не зависит от жизненного цикла задач и пользователей.

CREATE TABLE IF NOT EXISTS uniqueness_analytics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL,
    user_id INT DEFAULT NULL,
    score DECIMAL(5,2) DEFAULT 0.00 COMMENT 'Итоговый процент уникальности',
    total_shingles INT DEFAULT 0 COMMENT 'Всего шинглов в тексте',
    checked_shingles INT DEFAULT 0 COMMENT 'Проверено шинглов',
    non_unique_shingles INT DEFAULT 0 COMMENT 'Неуникальных шинглов',
    cache_hits INT DEFAULT 0 COMMENT 'Попаданий в кеш',
    api_calls INT DEFAULT 0 COMMENT 'Запросов к API',
    limits_spent INT DEFAULT 0 COMMENT 'Потрачено лимитов',
    text_length INT DEFAULT 0 COMMENT 'Длина исходного текста в символах',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Время завершения проверки',
    
    UNIQUE INDEX idx_task_id (task_id),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Персистентная аналитика проверок уникальности';
