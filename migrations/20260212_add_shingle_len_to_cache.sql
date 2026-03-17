-- Миграция: Поддержка многослойного кеша (по длине шингла)
-- Дата: 12.02.2026

-- 1. Добавляем колонку shingle_len
ALTER TABLE shingles_cache ADD COLUMN shingle_len TINYINT UNSIGNED DEFAULT 4 AFTER shingle_hash;

-- 2. Обновляем первичный ключ (делаем его составным)
-- Сначала удаляем старый PK
ALTER TABLE shingles_cache DROP PRIMARY KEY;

-- 3. Добавляем новый составной PK
ALTER TABLE shingles_cache ADD PRIMARY KEY (shingle_hash, shingle_len);

-- 4. Добавляем индекс для быстрой фильтрации по длине
CREATE INDEX idx_shingle_len ON shingles_cache (shingle_len);
