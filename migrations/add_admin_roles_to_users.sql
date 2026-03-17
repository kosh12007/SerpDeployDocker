ALTER TABLE users
ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN is_super_admin BOOLEAN NOT NULL DEFAULT FALSE;

-- Назначаем первого пользователя суперадминистратором
UPDATE users SET is_super_admin = TRUE, is_admin = TRUE WHERE id = 1;