-- Миграция: Добавление таблицы для персистентной статистики доменов
-- Описание: Создает таблицу uniqueness_source_domains для хранения количества совпадений по доменам

CREATE TABLE IF NOT EXISTS uniqueness_source_domains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    match_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_domain (domain),
    -- Не используем FOREIGN KEY на uniqueness_tasks, чтобы данные оставались после удаления задач
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
