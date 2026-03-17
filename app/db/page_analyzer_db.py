import mysql.connector
from mysql.connector import Error
import logging
import os
import json
from .database import create_connection

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "page_analyzer_db.log")
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


def create_page_analysis_task(user_id):
    """Создает новую задачу анализа страниц для пользователя."""
    try:
        connection = create_connection()
        if not connection:
            logger.error(
                "Не удалось создать подключение к базе данных для создания задачи анализа."
            )
            return None

        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO page_analysis_tasks (user_id) VALUES (%s)", (user_id,)
        )
        task_id = cursor.lastrowid
        connection.commit()
        logger.info(
            f"Создана новая задача анализа страниц с ID {task_id} для пользователя {user_id}."
        )
        return task_id

    except Error as e:
        logger.error(f"Ошибка при создании задачи анализа страниц: {e}", exc_info=True)
        return None
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def save_page_analysis_result(task_id, url, analysis_results):
    """Сохраняет результаты анализа страницы в базу данных."""
    try:
        connection = create_connection()
        if not connection:
            logger.error(
                "Не удалось создать подключение к базе данных для сохранения результатов анализа."
            )
            return False

        cursor = connection.cursor()

        # Преобразуем списки/словари в JSON-строки
        lsi_words_json = (
            json.dumps(analysis_results.get("lsi_words"), ensure_ascii=False)
            if analysis_results.get("lsi_words") is not None
            else None
        )
        headings_json = (
            json.dumps(analysis_results.get("headings"), ensure_ascii=False)
            if analysis_results.get("headings") is not None
            else None
        )

        query = """
        INSERT INTO page_analysis_results (task_id, url, lsi_words, text_length, title, description, headings)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        data = (
            task_id,
            url,
            lsi_words_json,
            analysis_results.get("text_length"),
            analysis_results.get("title"),
            analysis_results.get("description"),
            headings_json,
        )

        cursor.execute(query, data)
        connection.commit()
        logger.info(
            f"Результаты анализа для URL {url} (задача {task_id}) успешно сохранены."
        )
        return True

    except Error as e:
        logger.error(
            f"Ошибка при сохранении результатов анализа для URL {url}: {e}",
            exc_info=True,
        )
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def delete_page_analysis_task(task_id, user_id):
    """Удаляет задачу анализа страниц и все связанные с ней результаты."""
    try:
        connection = create_connection()
        if not connection:
            logger.error(
                "Не удалось создать подключение к базе данных для удаления задачи."
            )
            return False

        cursor = connection.cursor()

        # Проверяем, что задача принадлежит пользователю
        cursor.execute(
            "SELECT id FROM page_analysis_tasks WHERE id = %s AND user_id = %s",
            (task_id, user_id),
        )
        if cursor.fetchone() is None:
            logger.warning(
                f"Попытка удаления задачи {task_id} пользователем {user_id}, но задача не найдена или не принадлежит ему."
            )
            return False

        cursor.execute("DELETE FROM page_analysis_tasks WHERE id = %s", (task_id,))
        connection.commit()
        logger.info(f"Задача анализа страниц с ID {task_id} успешно удалена.")
        return True

    except Error as e:
        logger.error(
            f"Ошибка при удалении задачи анализа страниц {task_id}: {e}", exc_info=True
        )
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
