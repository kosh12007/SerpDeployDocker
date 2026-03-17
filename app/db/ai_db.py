import logging
import os
from mysql.connector import Error
from .database import create_connection

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "ai_db.log")
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


def create_ai_task(user_id, system_prompt):
    """Создает новую задачу для AI в базе данных."""
    sql = "INSERT INTO ai_tasks (user_id, system_prompt, status) VALUES (%s, %s, %s)"
    conn = create_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, system_prompt, "pending"))
        task_id = cursor.lastrowid
        conn.commit()
        logger.info(f"Создана AI-задача с ID {task_id} для пользователя {user_id}.")
        return task_id
    except Error as e:
        logger.error(
            f"Ошибка при создании AI-задачи для пользователя {user_id}: {e}",
            exc_info=True,
        )
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def get_ai_tasks_by_user(user_id):
    """Получает все AI-задачи для указанного пользователя."""
    sql = "SELECT * FROM ai_tasks WHERE user_id = %s ORDER BY created_at DESC"
    conn = create_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, (user_id,))
        tasks = cursor.fetchall()
        return tasks
    except Error as e:
        logger.error(
            f"Ошибка при получении AI-задач для пользователя {user_id}: {e}",
            exc_info=True,
        )
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def get_ai_results_by_task(task_id):
    """Получает все результаты для указанной AI-задачи."""
    sql = "SELECT * FROM ai_results WHERE task_id = %s ORDER BY created_at ASC"
    conn = create_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, (task_id,))
        results = cursor.fetchall()
        return results
    except Error as e:
        logger.error(
            f"Ошибка при получении результатов для AI-задачи {task_id}: {e}",
            exc_info=True,
        )
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def delete_ai_task(task_id, user_id):
    """Удаляет AI-задачу, если она принадлежит пользователю."""
    conn = create_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        # Сначала проверяем, что задача принадлежит пользователю
        cursor.execute("SELECT user_id FROM ai_tasks WHERE id = %s", (task_id,))
        task = cursor.fetchone()
        if not task or task[0] != user_id:
            logger.warning(
                f"Попытка пользователя {user_id} удалить чужую AI-задачу {task_id}."
            )
            return False

        # Удаляем задачу (каскадное удаление удалит и результаты)
        cursor.execute("DELETE FROM ai_tasks WHERE id = %s", (task_id,))
        conn.commit()
        logger.info(
            f"AI-задача {task_id} была успешно удалена пользователем {user_id}."
        )
        return True
    except Error as e:
        logger.error(f"Ошибка при удалении AI-задачи {task_id}: {e}", exc_info=True)
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def update_ai_task_status(task_id, status):
    """Обновляет статус AI-задачи."""
    sql = "UPDATE ai_tasks SET status = %s WHERE id = %s"
    conn = create_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (status, task_id))
        conn.commit()
    except Error as e:
        logger.error(
            f"Ошибка при обновлении статуса для AI-задачи {task_id}: {e}", exc_info=True
        )
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def save_ai_result(task_id, user_message, ai_response):
    """Сохраняет результат выполнения AI-задачи."""
    sql = "INSERT INTO ai_results (task_id, user_message, ai_response) VALUES (%s, %s, %s)"
    conn = create_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (task_id, user_message, ai_response))
        conn.commit()
    except Error as e:
        logger.error(
            f"Ошибка при сохранении результата для AI-задачи {task_id}: {e}",
            exc_info=True,
        )
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
