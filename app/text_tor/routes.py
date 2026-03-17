from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from ..db.database import create_connection
from ..db.ai_db import get_ai_tasks_by_user, get_ai_results_by_task
import json
from app.db_config import LOGGING_ENABLED
import logging
import os

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "text_tor_routes.log")
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

text_tor_bp = Blueprint("text_tor", __name__, url_prefix="/text-tor")


@text_tor_bp.route("/create")
@login_required
def create_text_tor_page():
    """Отображает страницу 'Создать ТЗ на Текст' с данными на основе result_ids."""
    result_ids = request.args.getlist("result_ids", type=int)
    results = []

    if result_ids:
        try:
            with create_connection() as conn:
                with conn.cursor() as cursor:
                    # Создаем плейсхолдеры для каждого ID
                    placeholders = ", ".join(["%s"] * len(result_ids))

                    # Формируем безопасный SQL-запрос с плейсхолдерами
                    query = f"SELECT id, url, title, description, text_length, headings, lsi_words FROM page_analysis_results WHERE id IN ({placeholders})"

                    # Выполняем запрос, передавая ID в качестве параметров
                    cursor.execute(query, result_ids)

                    # Получаем все строки и преобразуем их в словари
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    results = [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            print(f"Ошибка при получении данных: {e}")
            # В случае ошибки можно передать пустой список или сообщение об ошибке
            results = []

    # Получаем задачи AI
    ai_tasks = get_ai_tasks_by_user(current_user.id)
    for task in ai_tasks:
        task["results"] = get_ai_results_by_task(task["id"])

    # Передаем from_json, полученные результаты и задачи AI в шаблон
    return render_template(
        "create_text_tor.html", results=results, from_json=json.loads, ai_tasks=ai_tasks
    )


@text_tor_bp.route("/task-status/<int:task_id>")
@login_required
def task_status(task_id):
    """Возвращает статус и результат задачи AI."""
    try:
        with create_connection() as conn:
            # Указываем, что хотим получать результаты в виде словаря
            with conn.cursor(dictionary=True) as cursor:
                # Получаем задачу
                cursor.execute(
                    "SELECT id, user_id, status FROM ai_tasks WHERE id = %s", (task_id,)
                )
                task = cursor.fetchone()

                if not task or task["user_id"] != current_user.id:
                    return {
                        "status": "error",
                        "message": "Задача не найдена или у вас нет доступа.",
                    }, 404

                response_data = {
                    "status": task["status"],
                    "progress": 0,
                }  # Предполагаем прогресс 0

                if task["status"] == "completed":
                    # Получаем результат
                    cursor.execute(
                        "SELECT ai_response FROM ai_results WHERE task_id = %s ORDER BY id DESC LIMIT 1",
                        (task_id,),
                    )
                    result = cursor.fetchone()
                    if result:
                        response_data["ai_response"] = result["ai_response"]
                        if LOGGING_ENABLED:
                            logger.info(
                                f"Task {task_id} completed. Response found. Length: {len(str(result['ai_response']))} chars."
                            )
                    else:
                        response_data["ai_response"] = None
                        if LOGGING_ENABLED:
                            logger.warning(
                                f"Task {task_id} completed but NO response found in ai_results table."
                            )
                    response_data["progress"] = 100

                elif task["status"] == "running":
                    response_data["progress"] = (
                        50  # Примерный прогресс для запущенной задачи
                    )

                return response_data

    except Exception as e:
        print(f"Ошибка при получении статуса задачи {task_id}: {e}")
        return {"status": "error", "message": "Внутренняя ошибка сервера."}, 500
