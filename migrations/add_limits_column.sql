-- Добавляем колонку limits, если её нет
SET @tablename = 'users';
SET @columnname = 'limits';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = DATABASE()) -- Используем текущую базу данных вместо переменной @dbname
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' INT NOT NULL DEFAULT 0')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;
