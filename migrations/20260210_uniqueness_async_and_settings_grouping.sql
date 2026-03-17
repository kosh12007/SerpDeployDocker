-- Миграция: Создание таблицы uniqueness_tasks и обновление таблицы settings
-- Описание: Создает таблицу для фоновых задач уникальности и добавляет колонку category в настройки

CREATE TABLE IF NOT EXISTS uniqueness_tasks (
    task_id VARCHAR(100) PRIMARY KEY,
    user_id INT,
    status ENUM('pending', 'running', 'completed', 'error') DEFAULT 'pending',
    progress_total INT DEFAULT 0,
    progress_current INT DEFAULT 0,
    result JSON,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Пробуем добавить колонку category в таблицу settings
-- (Используем процедуру для безопасного добавления, так как IF NOT EXISTS для колонок не поддерживается во многих версиях MySQL)
SET @dbname = DATABASE();
SET @tablename = 'settings';
SET @columnname = 'category';
SET @preparedStatement = (SELECT IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = @dbname
     AND TABLE_NAME = @tablename
     AND COLUMN_NAME = @columnname) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' VARCHAR(50) DEFAULT "General" AFTER description')
));
PREPARE stmt FROM @preparedStatement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Добавление новых настроек
INSERT IGNORE INTO settings (name, value, description, category) VALUES
('UNIQUENESS_THREADS', '5', 'Количество одновременных запросов к API для проверки уникальности.', 'Uniqueness');

-- Обновление категорий для существующих настроек
UPDATE settings SET category = 'Uniqueness' WHERE name LIKE 'UNIQUENESS_%';
UPDATE settings SET category = 'General' WHERE name IN ('DEFAULT_USER_LIMITS', 'MAX_QUERIES', 'ALLOW_REGISTRATION');
UPDATE settings SET category = 'HTTP' WHERE name = 'MAX_HTTP_STATUS_URLS';
