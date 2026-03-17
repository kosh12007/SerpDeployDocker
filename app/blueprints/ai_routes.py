"""
AI routes blueprint for SERP bot application.

Contains routes for:
- AI assistant page
- Article generator page
- Sending requests to AI
- Checking AI task status
- Downloading AI results
- Deleting AI tasks
"""

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    Response,
)
from flask_login import login_required, current_user
import os
import logging
import io
from ..config import DEEPSEEK_API_KEY
from ..db.database import create_connection
from ..db.ai_db import (
    create_ai_task,
    get_ai_tasks_by_user,
    get_ai_results_by_task,
    delete_ai_task as db_delete_ai_task,
)
from ..ai_thread import start_ai_analysis, ai_analysis_status
from mysql.connector import Error

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "ai_routes.log")
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

ai_routes = Blueprint("ai", __name__)


@ai_routes.route("/ai")
@login_required
def ai_page():
    """Отображает страницу AI ассистента с задачами и результатами."""
    tasks = get_ai_tasks_by_user(current_user.id)
    for task in tasks:
        task["results"] = get_ai_results_by_task(task["id"])
    return render_template("ai.html", tasks=tasks)


@ai_routes.route("/article-generator")
@login_required
def article_generator_page():
    """Отображает страницу генератора статей с задачами и результатами."""
    tasks = get_ai_tasks_by_user(current_user.id)
    for task in tasks:
        task["results"] = get_ai_results_by_task(task["id"])
    return render_template("article_generator.html", tasks=tasks)


@ai_routes.route("/ask-ai", methods=["POST"])
@login_required
def ask_ai():
    """Создает задачу для AI и запускает ее выполнение."""
    system_prompt = request.form.get("system_prompt")
    user_message = request.form.get("user_message")

    if not all([system_prompt, user_message]):
        return jsonify(
            {
                "status": "error",
                "message": "Системный промпт и сообщение пользователя не могут быть пустыми.",
            }
        )

    if not DEEPSEEK_API_KEY:
        return jsonify(
            {
                "status": "error",
                "message": "API-ключ для DeepSeek не настроен на сервере.",
            }
        )

    task_id = create_ai_task(current_user.id, system_prompt)

    if task_id:
        start_ai_analysis(task_id, system_prompt, user_message)
        # Возвращаем JSON с task_id для отслеживания
        return jsonify(
            {
                "status": "success",
                "message": "AI-задача успешно создана и поставлена в очередь на выполнение.",
                "task_id": task_id,
            }
        )
    else:
        # Возвращаем JSON с ошибкой
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Ошибка при создании AI-задачи в базе данных.",
                }
            ),
            500,
        )


@ai_routes.route("/ai-status/<int:task_id>")
@login_required
def ai_status_route(task_id):
    """Возвращает статус выполнения AI-задачи."""
    status = ai_analysis_status.get(
        task_id, {"status": "not_found", "progress": 0, "message": "Задача не найдена"}
    )
    return jsonify(status)


@ai_routes.route("/delete-ai-task/<int:task_id>", methods=["DELETE"])
@login_required
def delete_ai_task(task_id):
    """Удаляет AI-задачу и связанные с ней результаты."""
    if db_delete_ai_task(task_id, current_user.id):
        return jsonify(
            {
                "status": "success",
                "message": "Задача и все связанные данные успешно удалены.",
            }
        )
    else:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Ошибка при удалении задачи или у вас нет прав.",
                }
            ),
            500,
        )


@ai_routes.route("/download-ai-task/<int:task_id>")
@login_required
def download_ai_task(task_id):
    """Скачивает результаты AI-задачи."""
    format_type = request.args.get("format", "txt")

    connection = create_connection()
    if not connection:
        flash("Ошибка подключения к базе данных.", "danger")
        return redirect(url_for("ai.ai_page"))

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM ai_tasks WHERE id = %s AND user_id = %s",
            (task_id, current_user.id),
        )
        task = cursor.fetchone()

        if not task:
            flash("Задача не найдена или у вас нет к ней доступа.", "danger")
            return redirect(url_for("ai.ai_page"))

        cursor.execute("SELECT * FROM ai_results WHERE task_id = %s", (task_id,))
        results = cursor.fetchall()

        if not results:
            flash("Нет данных для скачивания по этой задаче.", "warning")
            return redirect(url_for("ai.ai_page"))

        base_filename = f"AI_Task_{task_id}_{task['created_at'].strftime('%Y-%m-%d')}"

        output = io.StringIO()
        output.write(f"--- Задача #{task_id} ---\n")
        output.write(
            f"Дата создания: {task['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
        )
        output.write(f"Системный промпт: {task['system_prompt']}\n\n")

        for i, res in enumerate(results, 1):
            output.write(f"--- Запрос #{i} ---\n")
            output.write(f"Пользователь: {res['user_message']}\n")
            output.write(f"AI Ответ: {res['ai_response']}\n\n")

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename={base_filename}.txt"
            },
        )

    except Error as e:
        logger.error(
            f"Ошибка базы данных при скачивании AI-задачи {task_id}: {e}", exc_info=True
        )
        flash("Ошибка базы данных при формировании файла.", "danger")
        return redirect(url_for("ai.ai_page"))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@ai_routes.route("/download-article-task/<int:task_id>")
@login_required
def download_article_task(task_id):
    """Скачивает результаты AI-задачи для генератора статей."""
    format_type = request.args.get("format", "txt")

    connection = create_connection()
    if not connection:
        flash("Ошибка подключения к базе данных.", "danger")
        return redirect(url_for("ai.article_generator_page"))

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM ai_tasks WHERE id = %s AND user_id = %s",
            (task_id, current_user.id),
        )
        task = cursor.fetchone()

        if not task:
            flash("Задача не найдена или у вас нет к ней доступа.", "danger")
            return redirect(url_for("ai.article_generator_page"))

        cursor.execute("SELECT * FROM ai_results WHERE task_id = %s", (task_id,))
        results = cursor.fetchall()

        if not results:
            flash("Нет данных для скачивания по этой задаче.", "warning")
            return redirect(url_for("ai.article_generator_page"))

        base_filename = (
            f"Article_Task_{task_id}_{task['created_at'].strftime('%Y-%m-%d')}"
        )

        output = io.StringIO()
        output.write(f"--- Задача #{task_id} ---\n")
        output.write(
            f"Дата создания: {task['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
        )
        output.write(f"Системный промпт: {task['system_prompt']}\n\n")

        for i, res in enumerate(results, 1):
            output.write(f"--- Запрос #{i} ---\n")
            output.write(f"Параметры:\n{res['user_message']}\n")
            output.write(f"AI Ответ:\n{res['ai_response']}\n\n")

        output.seek(0)
        return Response(
            output.getvalue().encode("utf-8"),
            mimetype="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename={base_filename}.txt"
            },
        )

    except Error as e:
        logger.error(
            f"Ошибка базы данных при скачивании AI-задачи {task_id}: {e}", exc_info=True
        )
        flash("Ошибка базы данных при формировании файла.", "danger")
        return redirect(url_for("ai.article_generator_page"))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
