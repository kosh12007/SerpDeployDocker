import logging
import os
from mysql.connector import Error
from .database import create_connection
from app.db_config import LOGGING_ENABLED

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "settings_db.log")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Отключаем передачу логов вышестоящим логгерам (консоли)
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
# --- Конец настройки логгера ---


def get_all_settings():
    if LOGGING_ENABLED:
        logger.info("Логер включен")
    """Получает все настройки из базы данных."""
    try:
        connection = create_connection()
        if not connection:
            logger.error("Не удалось установить соединение с базой данных.")
            return {}

        cursor = connection.cursor(dictionary=True)
        query = "SELECT name, value FROM settings"
        cursor.execute(query)
        settings_data = cursor.fetchall()

        settings = {item["name"]: item["value"] for item in settings_data}
        return settings
    except Error as e:
        logger.error(f"Ошибка при получении всех настроек: {e}", exc_info=True)
        return {}
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def get_setting(name):
    """Получает значение настройки по её имени."""
    try:
        connection = create_connection()
        if not connection:
            return None

        cursor = connection.cursor(dictionary=True)
        query = "SELECT value FROM settings WHERE name = %s"
        cursor.execute(query, (name,))
        setting_data = cursor.fetchone()

        return setting_data["value"] if setting_data else None
    except Error as e:
        logger.error(f"Ошибка при получении настройки '{name}': {e}", exc_info=True)
        return None
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def add_default_settings_if_not_exist():
    """Добавляет настройки по умолчанию, если они отсутствуют в БД."""
    try:
        connection = create_connection()
        if not connection:
            return

        cursor = connection.cursor(dictionary=True)

        # Настройки по умолчанию, которые нужно проверить
        default_settings = [
            {"name": "DEFAULT_USER_LIMITS", "value": "300", "category": "General"},
            {"name": "MAX_QUERIES", "value": "10", "category": "General"},
            {"name": "ALLOW_REGISTRATION", "value": "true", "category": "General"},
            {"name": "MAX_HTTP_STATUS_URLS", "value": "50", "category": "HTTP"},
            {
                "name": "UNIQUENESS_SHINGLE_LENGTH",
                "value": "3",
                "category": "Uniqueness",
            },
            {"name": "UNIQUENESS_SHINGLE_STEP", "value": "3", "category": "Uniqueness"},
            {"name": "UNIQUENESS_THREADS", "value": "5", "category": "Uniqueness"},
            {
                "name": "UNIQUENESS_SAMPLING_MODE",
                "value": "deterministic",
                "category": "Uniqueness",
            },
            {
                "name": "UNIQUENESS_CACHE_DISCOUNT",
                "value": "50",
                "category": "Uniqueness",
            },
            {
                "name": "UNIQUENESS_MIN_MATCH_PERCENT",
                "value": "2",
                "category": "Uniqueness",
            },
            {
                "name": "UNIQUENESS_MAX_MATCH_URLS",
                "value": "100",
                "category": "Uniqueness",
            },
            {
                "name": "UNIQUENESS_CACHE_TTL",
                "value": "14",
                "category": "Uniqueness",
            },
        ]

        for setting in default_settings:
            name = setting["name"]
            value = setting["value"]
            category = setting["category"]
            # Проверяем, существует ли настройка
            cursor.execute("SELECT 1 FROM settings WHERE name = %s", (name,))
            if not cursor.fetchone():
                # Если нет, добавляем
                insert_query = "INSERT INTO settings (name, value, description, category) VALUES (%s, %s, %s, %s)"
                description = (
                    f"Значение по умолчанию для {name.replace('_', ' ').title()}"
                )
                cursor.execute(insert_query, (name, value, description, category))
                if LOGGING_ENABLED:
                    logger.info(
                        f"Добавлена настройка по умолчанию: {name} = {value} (Категория: {category})"
                    )

        connection.commit()

    except Error as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при добавлении настроек по умолчанию: {e}", exc_info=True
            )
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def update_setting(name, value):
    """Обновляет значение настройки."""
    try:
        connection = create_connection()
        if not connection:
            return False

        cursor = connection.cursor()
        query = "UPDATE settings SET value = %s WHERE name = %s"
        cursor.execute(query, (value, name))
        connection.commit()
        return True
    except Error as e:
        logger.error(f"Ошибка при обновлении настройки '{name}': {e}", exc_info=True)
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
