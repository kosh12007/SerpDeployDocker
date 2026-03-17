"""
Top sites routes blueprint for SERP bot application.

Contains routes for:
- Top sites page
- Top sites parsing
- Top sites results management
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
import os
import logging
from ..db.database import create_connection, get_user_sessions_from_db
from ..region_utils import get_region_name_by_id
from ..top_sites_parser_thread import run_top_sites_parsing_thread
from ..utils import assign_duplicate_styles
from mysql.connector import Error

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "top_sites_routes.log")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# Важно: предотвращаем передачу логов родительским логгерам (в частности, root логгеру)
logger.propagate = False
if not logger.handlers:
    import logging

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
logger.info(f"Логгер для {__name__} настроен.")
# --- Конец настройки логгера ---

top_sites_routes = Blueprint("top_sites", __name__)


@top_sites_routes.route("/top-sites")
@login_required
def top_sites_page():
    """Отображает страницу 'Выгрузка ТОП-10 сайтов' с формой и результатами."""
    connection = create_connection()
    if not connection:
        flash("Ошибка подключения к базе данных.", "danger")
        from app.db.settings_db import get_setting

        max_queries = int(get_setting("MAX_QUERIES") or 5)
        return render_template("top_sites.html", tasks_data=[], max_queries=max_queries)

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM top_sites_tasks WHERE user_id = %s ORDER BY created_at DESC",
            (current_user.id,),
        )
        tasks = cursor.fetchall()

        tasks_data = []
        for task in tasks:
            task["region_name"] = get_region_name_by_id(
                task.get("search_engine"), task.get("region")
            )
            cursor.execute(
                "SELECT * FROM top_sites_queries WHERE task_id = %s", (task["id"],)
            )
            task_queries = cursor.fetchall()
            logger.debug(f"Task {task['id']} queries: {task_queries}")

            all_results_for_task = []
            query_ids_for_task = [q["id"] for q in task_queries]

            if query_ids_for_task:
                placeholders = ",".join(["%s"] * len(query_ids_for_task))
                result_sql = f"SELECT * FROM top_sites_results WHERE query_id IN ({placeholders}) ORDER BY position ASC"
                cursor.execute(result_sql, tuple(query_ids_for_task))
                all_results_for_task = cursor.fetchall()

            results_by_query_id = {}
            for res in all_results_for_task:
                q_id = res["query_id"]
                if q_id not in results_by_query_id:
                    results_by_query_id[q_id] = []
                results_by_query_id[q_id].append(res)

            for q in task_queries:
                q["results"] = results_by_query_id.get(q["id"], [])

            # Собираем все URL-ы из всех запросов в один список
            all_urls_for_task = [r["url"] for q in task_queries for r in q["results"]]
            logger.debug(
                f"All URLs for task {task['id']} sent to assign_duplicate_styles: {all_urls_for_task}"
            )

            duplicate_styles = assign_duplicate_styles(all_urls_for_task)
            logger.debug(
                f"Result from assign_duplicate_styles for task {task['id']}: {duplicate_styles}"
            )

            tasks_data.append(
                {
                    "task_info": task,
                    "queries": task_queries,
                    "duplicate_styles": duplicate_styles,
                }
            )

        from app.db.settings_db import get_setting

        max_queries = int(get_setting("MAX_QUERIES") or 5)
        return render_template(
            "top_sites.html", tasks_data=tasks_data, max_queries=max_queries
        )

    except Error as e:
        logger.error(
            f"Ошибка при получении данных для страницы 'ТОП-10': {e}", exc_info=True
        )
        flash("Произошла ошибка при получении данных.", "danger")
        from app.db.settings_db import get_setting

        max_queries = int(get_setting("MAX_QUERIES") or 5)
        return render_template("top_sites.html", tasks_data=[], max_queries=max_queries)
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@top_sites_routes.route("/start-top-sites-parsing", methods=["POST"])
@login_required
def start_top_sites_parsing():
    try:
        # queries_text = request.form.get('queries')
        queries_list = request.form.getlist("queries")
        search_engine = request.form.get("search_engine")
        # region = request.form.get('region') # Это поле больше не используется напрямую
        device = request.form.get("device")
        depth_str = request.form.get("depth")
        depth = int(depth_str) if depth_str and depth_str.isdigit() else 1
        yandex_type = request.form.get("yandex_type", "search_api")

        yandex_page_limit_str = request.form.get("yandex_page_limit")
        yandex_page_limit = (
            int(yandex_page_limit_str)
            if yandex_page_limit_str and yandex_page_limit_str.isdigit()
            else 1
        )

        google_page_limit_str = request.form.get("google_page_limit")
        google_page_limit = (
            int(google_page_limit_str)
            if google_page_limit_str and google_page_limit_str.isdigit()
            else 1
        )
        # Determine which loc_id to use
        # loc_id теперь передается как единое поле, не зависимо от поисковика
        loc_id_str = request.form.get("loc_id")
        if loc_id_str and loc_id_str != "undefined":
            loc_id = int(loc_id_str)
        else:
            # Если loc_id не предоставлен или 'undefined', используем значение по умолчанию
            loc_id = 213 if request.form.get("search_engine") == "yandex" else 20949

        user_id = current_user.id
        # Объединяем список фраз обратно в текст, разделенный новой строкой, если это необходимо для дальнейшей обработки
        queries_text = "\n".join(queries_list)
        logger.info(
            f"Запуск парсинга ТОП-10. Движок: {search_engine}, Тип Яндекса: {yandex_type}, Глубина: {depth}, Лимит страниц Yandex: {yandex_page_limit}, Лимит страниц Google: {google_page_limit}, Локация: {loc_id}"
        )
        logger.debug(
            f"Параметры парсинга ТОП-10: queries_list={queries_list}, search_engine={search_engine}, device={device}, depth={depth}, yandex_type={yandex_type}, yandex_page_limit={yandex_page_limit}, google_page_limit={google_page_limit}, loc_id={loc_id}"
        )

        queries = [q.strip() for q in queries_list if q.strip()]
        if not all([queries, search_engine, loc_id, device]):
            return jsonify({"error": "Отсутствуют обязательные параметры."}), 400

        # --- Проверка лимитов (основная логика вынесена в /estimate-limits) ---
        # Оставляем проверку на сервере для безопасности
        required_limits = 0
        queries_count = len(queries)
        if search_engine == "yandex" and yandex_type == "search_api":
            required_limits = queries_count
        else:
            page_limit = (
                google_page_limit if search_engine == "google" else yandex_page_limit
            )
            required_limits = queries_count * page_limit

        if current_user.limits < required_limits:
            return (
                jsonify(
                    {
                        "error": f"Недостаточно лимитов для выполнения задачи. Требуется: {required_limits}, у вас в наличии: {current_user.limits}."
                    }
                ),
                400,
            )
        # --- Конец проверки ---

        connection = create_connection()
        if not connection:
            return jsonify({"error": "Не удалось подключиться к базе данных."}), 500

        cursor = connection.cursor()

        task_sql = """
        INSERT INTO top_sites_tasks (user_id, search_engine, region, device, depth, status, yandex_type)
        VALUES (%s, %s, %s, %s, %s, 'running', %s)
        """
        cursor.execute(
            task_sql,
            (
                user_id,
                search_engine,
                loc_id,
                device,
                depth,
                yandex_type if search_engine == "yandex" else None,
            ),
        )
        task_id = cursor.lastrowid

        queries_to_process = []
        for query_text in queries:
            query_sql = (
                "INSERT INTO top_sites_queries (task_id, query_text) VALUES (%s, %s) "
            )
            cursor.execute(query_sql, (task_id, query_text))
            query_id = cursor.lastrowid
            queries_to_process.append({"id": query_id, "text": query_text})

        connection.commit()

        from threading import Thread

        thread = Thread(
            target=run_top_sites_parsing_thread,
            args=(
                task_id,
                queries_to_process,
                search_engine,
                loc_id,
                device,
                depth,
                yandex_type,
                yandex_page_limit,
                google_page_limit,
                user_id,
            ),
        )
        thread.start()

        return jsonify(
            {
                "status": "success",
                "message": f"Задача парсинга ТОП-10 запущена для {len(queries)} фраз. Будет списано примерно {required_limits} лимитов.",
                "task_id": task_id,
            }
        )

    except Exception as e:
        logger.error(f"Ошибка при запуске задачи парсинга ТОП-10: {e}", exc_info=True)
        if "connection" in locals() and connection.is_connected():
            connection.rollback()
        return jsonify({"error": "Внутренняя ошибка сервера при запуске задачи."}), 500
    finally:
        if "cursor" in locals():
            cursor.close()
        if "connection" in locals() and connection.is_connected():
            connection.close()


@top_sites_routes.route("/estimate-limits", methods=["POST"])
@login_required
def estimate_limits():
    """
    Оценивает и возвращает необходимое количество лимитов для задачи парсинга.
    """
    try:
        logger.debug(f"Запрос на оценку лимитов. Request form: {request.form}")
        # Данные приходят как form-data, а не JSON. Используем request.form.
        # request.form.getlist используется для получения всех значений с одинаковым именем,
        # на случай если фронтенд будет отправлять несколько полей 'queries'.
        queries_list = request.form.getlist("queries")
        search_engine = request.form.get("search_engine")
        yandex_type = request.form.get("yandex_type", "search_api")
        yandex_page_limit = int(request.form.get("yandex_page_limit", 1))
        google_page_limit = int(request.form.get("google_page_limit", 1))

        queries = [q.strip() for q in queries_list if q.strip()]
        if not queries:
            return jsonify({"error": "Список запросов пуст."}), 400

        # --- Логика прогнозирования лимитов ---
        required_limits = 0
        queries_count = len(queries)

        if search_engine == "yandex" and yandex_type == "search_api":
            required_limits = queries_count
        else:  # Live Search или Google
            page_limit = (
                google_page_limit if search_engine == "google" else yandex_page_limit
            )
            required_limits = queries_count * page_limit

        return jsonify(
            {
                "estimated_limits": required_limits,
                "available_limits": current_user.limits,
            }
        )

    except Exception as e:
        logger.error(f"Ошибка при оценке лимитов: {e}", exc_info=True)
        return jsonify({"error": "Внутренняя ошибка сервера при оценке лимитов."}), 500


@top_sites_routes.route("/estimate-limits-parser", methods=["POST"])
@login_required
def estimate_limits_parser():
    """
    Оценивает и возвращает необходимое количество лимитов для задачи парсинга позиций.
    """
    try:
        logger.debug(f"Запрос на оценку лимитов парсера. Request form: {request.form}")
        queries_text = request.form.get("queries", "")
        engine = request.form.get("engine")
        yandex_type = request.form.get("yandex_type", "search_api")
        yandex_page_limit = int(request.form.get("yandex_page_limit", 1))
        google_page_limit = int(request.form.get("google_page_limit", 1))

        queries = [q.strip() for q in queries_text.splitlines() if q.strip()]
        if not queries:
            return jsonify({"error": "Список запросов пуст."}), 400

        required_limits = 0
        queries_count = len(queries)

        if engine == "yandex" and yandex_type == "search_api":
            required_limits = queries_count
        else:  # Live Search или Google
            page_limit = google_page_limit if engine == "google" else yandex_page_limit
            required_limits = queries_count * page_limit

        return jsonify(
            {
                "estimated_limits": required_limits,
                "available_limits": current_user.limits,
            }
        )

    except Exception as e:
        logger.error(f"Ошибка при оценке лимитов парсера: {e}", exc_info=True)
        return jsonify({"error": "Внутренняя ошибка сервера при оценке лимитов."}), 500


@top_sites_routes.route("/download-top-sites/<int:task_id>")
@login_required
def download_top_sites_task(task_id):
    from flask import send_file

    format_type = request.args.get("format", "xlsx")

    connection = create_connection()
    if not connection:
        flash("Ошибка подключения к базе данных.", "danger")
        return redirect(url_for("top_sites.top_sites_page"))

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM top_sites_tasks WHERE id = %s AND user_id = %s",
            (task_id, current_user.id),
        )
        task_info = cursor.fetchone()

        if not task_info:
            flash("Задача не найдена или у вас нет к ней доступа.", "danger")
            return redirect(url_for("top_sites.top_sites_page"))

        # Получаем первую фразу для имени файла
        cursor.execute(
            "SELECT query_text FROM top_sites_queries WHERE task_id = %s ORDER BY id LIMIT 1",
            (task_id,),
        )
        first_query = cursor.fetchone()
        first_query_text = (
            first_query["query_text"].replace(" ", "_") if first_query else ""
        )

        # Получаем имя региона
        region_name = get_region_name_by_id(
            task_info.get("search_engine"), task_info.get("region")
        )

        # Формируем имя файла
        filename_parts = [
            f"Задача_{task_id}",
            task_info["search_engine"],
        ]
        if task_info.get("yandex_type"):
            filename_parts.append(task_info["yandex_type"])

        filename_parts.extend(
            [
                region_name,
                task_info["device"],
                task_info["created_at"].strftime("%Y-%m-%d"),
                first_query_text,
            ]
        )

        base_filename = "_".join(filter(None, filename_parts))

        sql = """
        SELECT tq.query_text, tr.position, tr.url
        FROM top_sites_results tr
        JOIN top_sites_queries tq ON tr.query_id = tq.id
        WHERE tq.task_id = %s
        ORDER BY tq.id, tr.position
        """
        cursor.execute(sql, (task_id,))
        results = cursor.fetchall()

        if not results:
            flash("Нет данных для скачивания по этой задаче.", "warning")
            return redirect(url_for("top_sites.top_sites_page"))

        import io
        import csv
        import pandas as pd

        if format_type == "csv_utf8" or format_type == "csv_win1251":
            encoding = "utf-8" if format_type == "csv_utf8" else "windows-1251"
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Запрос", "Позиция", "URL"])
            for res in results:
                writer.writerow([res["query_text"], res["position"], res["url"]])

            output.seek(0)
            return send_file(
                io.BytesIO(output.read().encode(encoding)),
                mimetype="text/csv",
                as_attachment=True,
                download_name=f"{base_filename}.csv",
            )
        elif format_type == "txt":
            output = io.StringIO()
            current_query = None
            for res in results:
                if res["query_text"] != current_query:
                    current_query = res["query_text"]
                    output.write(f"\n--- Результаты для запроса: {current_query} ---\n")
                output.write(f"{res['position']}. {res['url']}\n")

            output.seek(0)
            return send_file(
                io.BytesIO(output.read().encode("utf-8")),
                mimetype="text/plain",
                as_attachment=True,
                download_name=f"{base_filename}.txt",
            )
        else:  # xlsx по умолчанию
            df = pd.DataFrame(results, columns=["query_text", "position", "url"])
            df.rename(
                columns={"query_text": "Запрос", "position": "Позиция", "url": "URL"},
                inplace=True,
            )

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
        return redirect(url_for("top_sites.top_sites_page"))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@top_sites_routes.route("/delete-top-sites/<int:task_id>", methods=["DELETE"])
@login_required
def delete_top_sites_task(task_id):
    connection = create_connection()
    if not connection:
        return (
            jsonify(
                {"status": "error", "message": "Ошибка подключения к базе данных."}
            ),
            500,
        )

    try:
        cursor = connection.cursor()

        cursor.execute("SELECT user_id FROM top_sites_tasks WHERE id = %s", (task_id,))
        task = cursor.fetchone()
        if not task or task[0] != current_user.id:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "У вас нет прав на удаление этой задачи.",
                    }
                ),
                403,
            )

        cursor.execute("DELETE FROM top_sites_tasks WHERE id = %s", (task_id,))
        connection.commit()

        return jsonify(
            {
                "status": "success",
                "message": "Задача и все связанные данные успешно удалены.",
            }
        )

    except Error as e:
        logger.error(
            f"Ошибка базы данных при удалении задачи {task_id}: {e}", exc_info=True
        )
        return (
            jsonify({"status": "error", "message": "Ошибка базы данных при удалении."}),
            500,
        )
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
