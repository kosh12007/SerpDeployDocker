-- Миграция: Добавление настройки MAX_HTTP_STATUS_URLS
-- Дата: 2026-01-18
-- Описание: Добавляет настройку для ограничения количества URL при проверке HTTP статусов

INSERT INTO settings (name, value, description)
VALUES (
    'MAX_HTTP_STATUS_URLS',
    '50',
    'Максимальное количество URL для проверки HTTP статусов'
)
ON DUPLICATE KEY UPDATE
    value = VALUES(value),
    description = VALUES(description);
