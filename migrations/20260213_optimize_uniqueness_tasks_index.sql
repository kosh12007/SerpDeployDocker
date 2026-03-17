-- Миграция: Оптимизация таблицы uniqueness_tasks
-- Описание: Добавляет индекс на user_id и created_at для ускорения получения истории задач и предотвращения ошибки "Out of sort memory"

ALTER TABLE uniqueness_tasks ADD INDEX idx_user_created (user_id, created_at DESC);
ALTER TABLE shingles_cache ADD INDEX idx_unique_updated (is_unique, last_updated DESC);
