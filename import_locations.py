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


def import_locations_from_csv(filepath):
    """Импортирует локации из CSV файла в базу данных."""
    try:
        # Указываем разделитель и названия колонок
        df = pd.read_csv(filepath, sep=";")
        df.columns = [
            "criteria_id",
            "name",
            "canonical_name",
            "parent_id",
            "country_code",
            "target_type",
            "status",
        ]

        connection = create_connection()
        if not connection:
            logger.error("Не удалось подключиться к базе данных для импорта локаций.")
            return

        cursor = connection.cursor()

        # Очистим таблицу перед вставкой новых данных
        cursor.execute("TRUNCATE TABLE locations")

        insert_query = """
        INSERT INTO locations (criteria_id, name, canonical_name, parent_id, country_code, target_type, status) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        for index, row in df.iterrows():
            try:
                # Преобразуем parent_id в int, обрабатывая возможные пустые значения
                parent_id = (
                    int(row["parent_id"]) if pd.notna(row["parent_id"]) else None
                )

                cursor.execute(
                    insert_query,
                    (
                        row["criteria_id"],
                        row["name"],
                        row["canonical_name"],
                        parent_id,
                        row["country_code"],
                        row["target_type"],
                        row["status"],
                    ),
                )
            except Error as e:
                logger.error(
                    f"Ошибка вставки строки {index + 2}: {row.to_dict()}. Ошибка: {e}"
                )
            except (ValueError, TypeError) as e:
                logger.error(
                    f"Ошибка преобразования данных в строке {index + 2}: {row.to_dict()}. Ошибка: {e}"
                )

        connection.commit()
        logger.info(f"Успешно импортировано {len(df)} локаций.")

    except FileNotFoundError:
        logger.error(f"Файл не найден: {filepath}")
    except Exception as e:
        logger.error(f"Произошла ошибка при импорте локаций: {e}", exc_info=True)
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


# if __name__ == "__main__":
#     import_locations_from_csv('geo (1).csv')
