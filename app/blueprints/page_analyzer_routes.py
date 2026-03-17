"""
Page analyzer routes blueprint for SERP bot application.

Contains routes for:
- Page analyzer page
- Analyzing pages
- Checking analysis status
- Downloading analysis results
- Deleting analysis tasks
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
import csv
import pandas as pd
import json
from ..db.database import create_connection
from ..db.page_analyzer_db import (
    create_page_analysis_task,
    save_page_analysis_result,
    delete_page_analysis_task,
)
from ..page_analyzer_thread import start_analysis, analysis_status
from mysql.connector import Error

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "page_analyzer_routes.log")
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

page_analyzer_routes = Blueprint("page_analyzer", __name__)


@page_analyzer_routes.route("/page-analyzer")
@login_required
def page_analyzer():
    """Отображает страницу анализатора страниц."""
    connection = create_connection()
    if not connection:
        flash("Ошибка подключения к базе данных.", "danger")
        return render_template("page_analyzer.html", tasks=[])

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM page_analysis_tasks WHERE user_id = %s ORDER BY created_at DESC",
            (current_user.id,),
        )
        tasks = cursor.fetchall()

        for task in tasks:
            cursor.execute(
                "SELECT * FROM page_analysis_results WHERE task_id = %s", (task["id"],)
            )
            task["results"] = cursor.fetchall()

        return render_template("page_analyzer.html", tasks=tasks, from_json=json.loads)
    except Error as e:
        flash(f"Ошибка при загрузке задач: {e}", "danger")
        return render_template("page_analyzer.html", tasks=[])
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@page_analyzer_routes.route("/analyze-pages", methods=["POST"])
@login_required
def analyze_pages():
    """Обрабатывает запрос на анализ нескольких страниц."""
    data = request.get_json()
    urls_input = data.get("urls")

    if not urls_input:
        return jsonify({"error": "URL не указаны"}), 400

    # Разделяем строку по http:// и https://, сохраняя разделители
    import re

    urls_raw = re.split(r"(https?://)", "".join(urls_input))

    urls = []
    for i in range(1, len(urls_raw), 2):
        # Соединяем протокол (http:// или https://) со следующей частью URL
        # и очищаем от лишних пробелов
        full_url = (urls_raw[i] + urls_raw[i + 1]).strip()
        if full_url:
            urls.append(full_url)

    if not urls:
        return jsonify({"error": "Корректные URL не найдены"}), 400

    task_id = create_page_analysis_task(current_user.id)
    if not task_id:
        return jsonify({"error": "Не удалось создать задачу для анализа"}), 500

    start_analysis(task_id, urls)

    return jsonify({"status": "started", "task_id": task_id})


@page_analyzer_routes.route("/analysis-status/<int:task_id>")
@login_required
def analysis_status_route(task_id):
    """Возвращает статус задачи анализа."""
    status = analysis_status.get(
        task_id, {"total": 0, "completed": 0, "status": "not_found", "progress": 0}
    )
    return jsonify(status)


@page_analyzer_routes.route("/download-analysis/<int:task_id>")
@login_required
def download_analysis_task(task_id):
    from flask import send_file

    format_type = request.args.get("format", "xlsx")

    connection = create_connection()
    if not connection:
        flash("Ошибка подключения к базе данных.", "danger")
        return redirect(url_for("page_analyzer.page_analyzer"))

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM page_analysis_tasks WHERE id = %s AND user_id = %s",
            (task_id, current_user.id),
        )
        task_info = cursor.fetchone()

        if not task_info:
            flash("Задача не найдена или у вас нет к ней доступа.", "danger")
            return redirect(url_for("page_analyzer.page_analyzer"))

        cursor.execute(
            "SELECT * FROM page_analysis_results WHERE task_id = %s", (task_id,)
        )
        results = cursor.fetchall()

        if not results:
            flash("Нет данных для скачивания по этой задаче.", "warning")
            return redirect(url_for("page_analyzer.page_analyzer"))

        base_filename = (
            f"Analysis_Task_{task_id}_{task_info['created_at'].strftime('%Y-%m-%d')}"
        )

        # --- Подготовка данных в формате XLSX ---
        import html

        new_results = []
        for res in results:
            lsi_words = []
            if res["lsi_words"] and isinstance(res["lsi_words"], str):
                try:
                    lsi_data = json.loads(res["lsi_words"])
                    # Если lsi_data - это строка (из-за двойного кодирования), пробуем декодировать еще раз
                    if isinstance(lsi_data, str):
                        lsi_data = json.loads(lsi_data)
                    if isinstance(lsi_data, list):
                        lsi_words = lsi_data
                except (json.JSONDecodeError, TypeError):
                    # Если это просто строка, не являющаяся JSON, оставляем как есть
                    lsi_words = [res["lsi_words"]]

            headings = (
                json.loads(res["headings"])
                if res["headings"] and isinstance(res["headings"], str)
                else []
            )

            max_len = max(len(lsi_words), len(headings), 1)

            for i in range(max_len):
                new_row = {
                    "url": res["url"] if i == 0 else "",
                    "title": (
                        html.unescape(res["title"]) if i == 0 and res["title"] else ""
                    ),
                    "description": (
                        html.unescape(res["description"])
                        if i == 0 and res["description"]
                        else ""
                    ),
                    "text_length": res["text_length"] if i == 0 else "",
                    "lsi_word": lsi_words[i] if i < len(lsi_words) else "",
                    "heading_level": (
                        f"H{headings[i]['level']}" if i < len(headings) else ""
                    ),
                    "heading_text": (
                        html.unescape(headings[i]["text"])
                        if i < len(headings) and headings[i].get("text")
                        else ""
                    ),
                }
                new_results.append(new_row)

        df = pd.DataFrame(new_results)

        # --- Перевод заголовков ---
        df.rename(
            columns={
                "url": "URL",
                "title": "Title",
                "description": "Description",
                "text_length": "Длина текста",
                "lsi_word": "LSI-слова",
                "heading_level": "Уровень заголовка",
                "heading_text": "Текст заголовка",
            },
            inplace=True,
        )

        # --- Выгрузка в запрошенном формате ---
        if format_type == "csv_utf8" or format_type == "csv_win1251":
            encoding = "utf-8" if format_type == "csv_utf8" else "windows-1251"
            output = io.StringIO()
            writer = csv.writer(output)

            writer.writerow(
                [
                    "URL",
                    "Title",
                    "Description",
                    "Длина текста",
                    "LSI-слова",
                    "Уровень заголовка",
                    "Текст заголовка",
                ]
            )

            for result in results:
                lsi_words = "N/A"
                if result["lsi_words"] and isinstance(result["lsi_words"], str):
                    try:
                        lsi_data = json.loads(result["lsi_words"])
                        if isinstance(lsi_data, list):
                            lsi_words = ", ".join(lsi_data)
                        else:
                            lsi_words = str(lsi_data)
                    except (json.JSONDecodeError, TypeError):
                        lsi_words = result[
                            "lsi_words"
                        ]  # Если это уже строка, а не JSON

                headings_str = "N/A"
                if result["headings"] and isinstance(result["headings"], str):
                    try:
                        headings_data = json.loads(result["headings"])
                        headings_str = "\n".join(
                            [
                                f"H{h['level']}: {html.unescape(h['text'])}"
                                for h in headings_data
                            ]
                        )
                    except json.JSONDecodeError:
                        pass

                writer.writerow(
                    [
                        result["url"],
                        html.unescape(result["title"]) if result["title"] else "",
                        (
                            html.unescape(result["description"])
                            if result["description"]
                            else ""
                        ),
                        result["text_length"],
                        lsi_words,
                        headings_str,
                    ]
                )

            csv_content = output.getvalue()
            output.close()

            return send_file(
                io.BytesIO(csv_content.encode(encoding, errors="replace")),
                mimetype="text/csv",
                as_attachment=True,
                download_name=f"{base_filename}.csv",
            )
        elif format_type == "txt":
            output = io.StringIO()
            # Используем исходные 'results' для более компактного вывода
            for res in results:
                output.write(f"--- URL: {res['url']} ---\n")
                output.write(
                    f"Title: {html.unescape(res['title']) if res['title'] else ''}\n"
                )
                output.write(
                    f"Description: {html.unescape(res['description']) if res['description'] else ''}\n"
                )
                output.write(f"Длина текста: {res['text_length']}\n")

                lsi_words_str = "N/A"
                if res["lsi_words"] and isinstance(res["lsi_words"], str):
                    try:
                        lsi_data = json.loads(res["lsi_words"])
                        if isinstance(lsi_data, list):
                            lsi_words_str = ", ".join(lsi_data)
                        else:
                            lsi_words_str = str(lsi_data)
                    except (json.JSONDecodeError, TypeError):
                        lsi_words_str = res[
                            "lsi_words"
                        ]  # Если это уже строка, а не JSON
                output.write(f"LSI-слова: {lsi_words_str}\n")

                headings_str = "N/A"
                if res["headings"] and isinstance(res["headings"], str):
                    try:
                        headings_data = json.loads(res["headings"])
                        headings_str = "\n".join(
                            [
                                f"H{h['level']}: {html.unescape(h['text'])}"
                                for h in headings_data
                            ]
                        )
                    except json.JSONDecodeError:
                        pass
                output.write(f"Заголовки:\n{headings_str}\n\n")

            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode("utf-8")),
                mimetype="text/plain",
                as_attachment=True,
                download_name=f"{base_filename}.txt",
            )
        else:  # xlsx по умолчанию
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name=f"Task_{task_id}")
            output.seek(0)

            return send_file(
                output,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=f"{base_filename}.xlsx",
            )

    except Error as e:
        logger.error(
            f"Ошибка базы данных при скачивании результатов задачи {task_id}: {e}",
            exc_info=True,
        )
        flash("Ошибка базы данных при формировании файла.", "danger")
        return redirect(url_for("page_analyzer.page_analyzer"))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@page_analyzer_routes.route("/delete-analysis/<int:task_id>", methods=["DELETE"])
@login_required
def delete_analysis_task_route(task_id):
    if delete_page_analysis_task(task_id, current_user.id):
        return jsonify({"status": "success", "message": "Задача успешно удалена."})
    else:
        return (
            jsonify({"status": "error", "message": "Ошибка при удалении задачи."}),
            500,
        )
