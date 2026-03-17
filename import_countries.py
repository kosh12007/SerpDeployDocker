import pandas as pd
from app.db.database import create_connection
from mysql.connector import Error
import logging
import os

# --- Настройка логгера ---
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "import.log")
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
logger.info(f"Логгер для {__name__} настроен.")
# --- Конец настройки логгера ---


def import_countries_from_excel(filepath):
    """Импортирует страны из Excel файла в базу данных."""
    try:
        df = pd.read_excel(filepath)
        # Убедимся, что колонки называются правильно
        df.columns = ["id", "code", "name"]

        connection = create_connection()
        if not connection:
            logger.error("Не удалось подключиться к базе данных для импорта стран.")
            return

        cursor = connection.cursor()

        # Очистим таблицу перед вставкой новых данных
        cursor.execute("TRUNCATE TABLE countries")

        insert_query = "INSERT INTO countries (id, code, name) VALUES (%s, %s, %s)"

        for index, row in df.iterrows():
            try:
                cursor.execute(insert_query, (row["id"], row["code"], row["name"]))
            except Error as e:
                logger.error(
                    f"Ошибка вставки строки {index + 2}: {row.to_dict()}. Ошибка: {e}"
                )

        connection.commit()
        logger.info(f"Успешно импортировано {len(df)} стран.")

    except FileNotFoundError:
        logger.error(f"Файл не найден: {filepath}")
    except Exception as e:
        logger.error(f"Произошла ошибка при импорте стран: {e}", exc_info=True)
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


if __name__ == "__main__":
    import_countries_from_excel("countries.xlsx")
