import os
from dotenv import load_dotenv
from app.db.settings_db import get_all_settings

# Загрузка настроек из .env
load_dotenv()

# --- Загрузка настроек из базы данных ---
try:
    try:
        db_settings = get_all_settings()
    except Exception:
        db_settings = {}
except Exception:
    db_settings = {}
# --- Конец загрузки настроек из базы данных ---

# Получаем режим из переменной окружения
MODE = os.getenv("MODE", "hosting")

# Получаем максимальное количество поисковых фраз из переменной окружения или БД
# MAX_QUERIES = int(db_settings.get("MAX_QUERIES", os.getenv("MAX_QUERIES", 10)))
# Эти настройки теперь получаются динамически, где это необходимо

# Получаем флаг разрешения регистрации из переменной окружения или БД
# ALLOW_REGISTRATION = db_settings.get("ALLOW_REGISTRATION", os.getenv("ALLOW_REGISTRATION", "true")).lower() == "true"

# Количество лимитов, выдаваемых пользователю при регистрации, из БД или .env
# DEFAULT_USER_LIMITS = int(db_settings.get("DEFAULT_USER_LIMITS", os.getenv("DEFAULT_USER_LIMITS", 300)))

# Флаг для включения/выключения логирования
# Настройка логирования была перенесена в каждый модуль индивидуально

# Ключ API для DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Настройка логирования была перенесена в каждый модуль индивидуально

class CacheConfig:
    CACHE_TYPE = 'SimpleCache'  # Используем простой кеш в памяти
    CACHE_DEFAULT_TIMEOUT = 300   # Время жизни кеша по умолчанию (в секундах)

class XmlRiverConfig(CacheConfig):
    """
    Конфигурация для клиента XmlRiver.
    """
    API_KEY = os.getenv('API_KEY')

class MailConfig:
    """
    Конфигурация для Flask-Mail.
    """
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')

class Config(XmlRiverConfig, CacheConfig, MailConfig):
    """Объединенный класс конфигурации."""
    # ВАЖНО: Секретный ключ должен быть постоянным и загружаться из переменных окружения.
    # Если ключ не задан, приложение не должно запускаться в production.
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("Отсутствует SECRET_KEY в переменных окружения. Этот ключ необходим для работы приложения.")
