-- Создание таблицы для хранения глобальных настроек приложения
CREATE TABLE settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    value VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT='Таблица для хранения глобальных настроек приложения.';

-- Добавление настроек по умолчанию
INSERT IGNORE INTO settings (name, value, description) VALUES
('DEFAULT_USER_LIMITS', '300', 'Количество лимитов, выдаваемых пользователю при регистрации.'),
('ALLOW_REGISTRATION', 'true', 'Разрешить (true) или запретить (false) регистрацию новых пользователей.'),
('MAX_QUERIES', '10', 'Максимальное количество поисковых фраз для парсинга за один раз.');