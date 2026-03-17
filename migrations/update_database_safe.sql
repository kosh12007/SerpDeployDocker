-- ============================================================
-- Безопасное обновление базы данных SERP
-- Проверяет существование таблиц и колонок перед созданием
-- Выполняет запросы в правильном порядке зависимостей
-- ============================================================

-- Отключаем проверку внешних ключей на время миграции
SET FOREIGN_KEY_CHECKS = 0;

-- Устанавливаем имя базы данных для проверок
SET @dbname = DATABASE();

-- ============================================================
-- 1. БАЗОВЫЕ ТАБЛИЦЫ (без зависимостей)
-- ============================================================

-- Таблица users
CREATE TABLE IF NOT EXISTS `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `reset_token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reset_token_expires` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `last_login` timestamp NULL DEFAULT NULL,
  `limits` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Добавляем колонку api_key, если её нет
SET @tablename = 'users';
SET @columnname = 'api_key';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL, ADD KEY idx_api_key (', @columnname, ')')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- ============================================================
-- 2. СПРАВОЧНИКИ (без зависимостей)
-- ============================================================

-- Таблица search_engines
CREATE TABLE IF NOT EXISTS `search_engines` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `api_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица devices
CREATE TABLE IF NOT EXISTS `devices` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `api_parameter` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица yandex_regions
CREATE TABLE IF NOT EXISTS `yandex_regions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `region_id` int NOT NULL,
  `region_name` varchar(255) NOT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `region_id` (`region_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Таблица locations
CREATE TABLE IF NOT EXISTS `locations` (
  `criteria_id` int NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `canonical_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `parent_id` int DEFAULT NULL,
  `country_code` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `target_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`criteria_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица search_types (зависит от search_engines)
CREATE TABLE IF NOT EXISTS `search_types` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `search_engine_id` int NOT NULL,
  `api_parameter` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_search_engine_id` (`search_engine_id`),
  CONSTRAINT `search_types_ibfk_1` FOREIGN KEY (`search_engine_id`) REFERENCES `search_engines` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 3. ПРОЕКТЫ И ЗАПРОСЫ
-- ============================================================

-- Таблица projects (зависит от users)
CREATE TABLE IF NOT EXISTS `projects` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  CONSTRAINT `projects_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица query_groups (зависит от projects)
CREATE TABLE IF NOT EXISTS `query_groups` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_project_id` (`project_id`),
  CONSTRAINT `query_groups_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица queries (зависит от projects и query_groups)
CREATE TABLE IF NOT EXISTS `queries` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `query_group_id` int DEFAULT NULL,
  `query_text` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `frequency` int DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_project_id` (`project_id`),
  KEY `idx_query_group_id` (`query_group_id`),
  CONSTRAINT `queries_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`),
  CONSTRAINT `queries_ibfk_2` FOREIGN KEY (`query_group_id`) REFERENCES `query_groups` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 4. ВАРИАНТЫ ПАРСИНГА
-- ============================================================

-- Таблица parsing_variants (зависит от projects, search_engines, search_types, yandex_regions, locations, devices)
CREATE TABLE IF NOT EXISTS `parsing_variants` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `search_engine_id` int NOT NULL,
  `search_type_id` int NOT NULL,
  `yandex_region_id` int DEFAULT NULL,
  `location_id` int DEFAULT NULL,
  `device_id` int NOT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `search_engine_id` (`search_engine_id`),
  KEY `search_type_id` (`search_type_id`),
  KEY `yandex_region_id` (`yandex_region_id`),
  KEY `location_id` (`location_id`),
  KEY `device_id` (`device_id`),
  KEY `idx_project_id` (`project_id`),
  CONSTRAINT `parsing_variants_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`),
  CONSTRAINT `parsing_variants_ibfk_2` FOREIGN KEY (`search_engine_id`) REFERENCES `search_engines` (`id`),
  CONSTRAINT `parsing_variants_ibfk_3` FOREIGN KEY (`search_type_id`) REFERENCES `search_types` (`id`),
  CONSTRAINT `parsing_variants_ibfk_4` FOREIGN KEY (`yandex_region_id`) REFERENCES `yandex_regions` (`region_id`),
  CONSTRAINT `parsing_variants_ibfk_5` FOREIGN KEY (`location_id`) REFERENCES `locations` (`criteria_id`),
  CONSTRAINT `parsing_variants_ibfk_6` FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Добавляем колонку page_limit, если её нет
SET @tablename = 'parsing_variants';
SET @columnname = 'page_limit';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' int DEFAULT ''10''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- ============================================================
-- 5. СТАРАЯ СИСТЕМА ПАРСИНГА
-- ============================================================

-- Таблица parsing_sessions (зависит от users)
CREATE TABLE IF NOT EXISTS `parsing_sessions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `session_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `domain` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `engine` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` enum('running','completed','error') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'running',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` timestamp NULL DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `session_id` (`session_id`),
  KEY `idx_user_id` (`user_id`),
  CONSTRAINT `parsing_sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Добавляем колонки для parsing_sessions, если их нет
SET @tablename = 'parsing_sessions';

-- Колонка region
SET @columnname = 'region';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Колонка device
SET @columnname = 'device';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Колонка depth
SET @columnname = 'depth';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' int DEFAULT NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Колонка yandex_type
SET @columnname = 'yandex_type';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Колонка spent_limits
SET @columnname = 'spent_limits';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' int NOT NULL DEFAULT ''0''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Таблица parsing_results (зависит от users)
CREATE TABLE IF NOT EXISTS `parsing_results` (
  `id` int NOT NULL AUTO_INCREMENT,
  `query` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `position` int DEFAULT NULL,
  `url` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `processed` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `user_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_user_id` (`user_id`),
  CONSTRAINT `parsing_results_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица session_results (зависит от parsing_sessions и parsing_results)
CREATE TABLE IF NOT EXISTS `session_results` (
  `session_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `result_id` int NOT NULL,
  PRIMARY KEY (`session_id`,`result_id`),
  KEY `result_id` (`result_id`),
  CONSTRAINT `session_results_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `parsing_sessions` (`session_id`) ON DELETE CASCADE,
  CONSTRAINT `session_results_ibfk_2` FOREIGN KEY (`result_id`) REFERENCES `parsing_results` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 6. НОВАЯ СИСТЕМА ПАРСИНГА ПОЗИЦИЙ
-- ============================================================

-- Таблица parsing_positions_sessions (зависит от users, projects, parsing_variants)
CREATE TABLE IF NOT EXISTS `parsing_positions_sessions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `project_id` int DEFAULT NULL,
  `parsing_variant_id` int DEFAULT NULL,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  `created_at` datetime DEFAULT NULL,
  `completed_at` datetime DEFAULT NULL,
  `spent_limits` int DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `project_id` (`project_id`),
  KEY `parsing_variant_id` (`parsing_variant_id`),
  CONSTRAINT `parsing_positions_sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `parsing_positions_sessions_ibfk_2` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`),
  CONSTRAINT `parsing_positions_sessions_ibfk_3` FOREIGN KEY (`parsing_variant_id`) REFERENCES `parsing_variants` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица parsing_position_results (зависит от queries и parsing_variants)
CREATE TABLE IF NOT EXISTS `parsing_position_results` (
  `id` int NOT NULL AUTO_INCREMENT,
  `query_id` int NOT NULL,
  `parsing_variant_id` int NOT NULL,
  `position` int DEFAULT NULL,
  `url_found` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `top_10_urls` json DEFAULT NULL,
  `date` date NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_query_id` (`query_id`),
  KEY `idx_parsing_variant_id` (`parsing_variant_id`),
  KEY `idx_date` (`date`),
  CONSTRAINT `parsing_position_results_ibfk_1` FOREIGN KEY (`query_id`) REFERENCES `queries` (`id`),
  CONSTRAINT `parsing_position_results_ibfk_2` FOREIGN KEY (`parsing_variant_id`) REFERENCES `parsing_variants` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица query_frequencies (зависит от queries и parsing_variants)
CREATE TABLE IF NOT EXISTS `query_frequencies` (
  `id` int NOT NULL AUTO_INCREMENT,
  `query_id` int NOT NULL,
  `parsing_variant_id` int NOT NULL,
  `frequency` int DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_frequency` (`query_id`,`parsing_variant_id`),
  KEY `idx_query_id` (`query_id`),
  KEY `idx_parsing_variant_id` (`parsing_variant_id`),
  CONSTRAINT `query_frequencies_ibfk_1` FOREIGN KEY (`query_id`) REFERENCES `queries` (`id`),
  CONSTRAINT `query_frequencies_ibfk_2` FOREIGN KEY (`parsing_variant_id`) REFERENCES `parsing_variants` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 7. ТОП-10 САЙТОВ
-- ============================================================

-- Таблица top_sites_tasks (зависит от users)
CREATE TABLE IF NOT EXISTS `top_sites_tasks` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `search_engine` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `region` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `device` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `depth` int DEFAULT NULL,
  `status` enum('running','completed','error') COLLATE utf8mb4_unicode_ci DEFAULT 'running',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `top_sites_tasks_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Добавляем колонки для top_sites_tasks, если их нет
SET @tablename = 'top_sites_tasks';

-- Колонка yandex_type
SET @columnname = 'yandex_type';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Колонка region_id
SET @columnname = 'region_id';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' int DEFAULT NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Колонка spent_limits
SET @columnname = 'spent_limits';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' int DEFAULT ''0''')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Таблица top_sites_queries (зависит от top_sites_tasks)
CREATE TABLE IF NOT EXISTS `top_sites_queries` (
  `id` int NOT NULL AUTO_INCREMENT,
  `task_id` int NOT NULL,
  `query_text` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` enum('pending','running','completed','error') COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  PRIMARY KEY (`id`),
  KEY `task_id` (`task_id`),
  CONSTRAINT `top_sites_queries_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `top_sites_tasks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица top_sites_results (зависит от top_sites_queries)
CREATE TABLE IF NOT EXISTS `top_sites_results` (
  `id` int NOT NULL AUTO_INCREMENT,
  `query_id` int NOT NULL,
  `url` varchar(1000) COLLATE utf8mb4_unicode_ci NOT NULL,
  `position` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `query_id` (`query_id`),
  CONSTRAINT `top_sites_results_ibfk_1` FOREIGN KEY (`query_id`) REFERENCES `top_sites_queries` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 8. АНАЛИЗАТОР СТРАНИЦ
-- ============================================================

-- Таблица page_analysis_tasks (зависит от users)
CREATE TABLE IF NOT EXISTS `page_analysis_tasks` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `status` enum('running','completed','error') COLLATE utf8mb4_unicode_ci DEFAULT 'running',
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `page_analysis_tasks_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица page_analysis_results (зависит от page_analysis_tasks)
CREATE TABLE IF NOT EXISTS `page_analysis_results` (
  `id` int NOT NULL AUTO_INCREMENT,
  `task_id` int NOT NULL,
  `url` varchar(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
  `lsi_words` json DEFAULT NULL,
  `text_length` int DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `headings` json DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `task_id` (`task_id`),
  CONSTRAINT `page_analysis_results_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `page_analysis_tasks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 9. AI ФУНКЦИОНАЛЬНОСТЬ
-- ============================================================

-- Таблица ai_tasks (зависит от users)
CREATE TABLE IF NOT EXISTS `ai_tasks` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `system_prompt` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `ai_tasks_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица ai_results (зависит от ai_tasks)
CREATE TABLE IF NOT EXISTS `ai_results` (
  `id` int NOT NULL AUTO_INCREMENT,
  `task_id` int NOT NULL,
  `user_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `ai_response` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `task_id` (`task_id`),
  CONSTRAINT `ai_results_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `ai_tasks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 10. ЗАГРУЗКА ФАЙЛОВ
-- ============================================================

-- Таблица upload_files (зависит от users и projects)
CREATE TABLE IF NOT EXISTS `upload_files` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `project_id` int NOT NULL,
  `filename` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `original_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_path` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `row_count` int DEFAULT '0',
  `status` enum('processing','completed','error') COLLATE utf8mb4_unicode_ci DEFAULT 'processing',
  `error_message` text COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `project_id` (`project_id`),
  CONSTRAINT `upload_files_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `upload_files_ibfk_2` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- ВКЛЮЧАЕМ ПРОВЕРКУ ВНЕШНИХ КЛЮЧЕЙ ОБРАТНО
-- ============================================================

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- КОНЕЦ МИГРАЦИИ
-- ============================================================
