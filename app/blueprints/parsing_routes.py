"""
Parsing routes blueprint for SERP bot application.

Contains routes for:
- Running parsing tasks
- Checking parsing status
- Downloading parsing results
- Managing parsing sessions
- Top sites parsing
- Limits estimation
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
import threading
import datetime
import uuid
import io
import csv
import pandas as pd
from ..config import MODE
from ..db.database import (
    create_connection,
    get_db_connection,
    get_user_sessions_from_db,
    get_results_from_db,
    update_session_status,
    spend_limit,
)
from ..positions_parsing.core.parser import run_positions_parsing_in_thread
from ..top_sites_parser_thread import run_top_sites_parsing_thread
from ..parsing import parsing_status, run_parsing_in_thread
from ..utils import assign_duplicate_styles
from mysql.connector import Error
from ..region_utils import get_region_name_by_id

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "parsing_routes.log")
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

parsing_routes = Blueprint("parsing", __name__)


@parsing_routes.route("/run", methods=["POST"])
@login_required
def run_parser():
    global parsing_status

    if parsing_status["is_running"]:
        logger.warning("Попытка запустить парсинг, когда он уже выполняется.")
        return (
            jsonify(
                {
                    "error": "Парсинг уже выполняется, дождитесь завершения предыдущего процесса"
                }
            ),
            400,
        )

    engine = request.form.get("engine", "google")
    queries = request.form.get("queries", "")
    domain = request.form.get("domain", "")
    yandex_type = request.form.get("yandex_type", "search_api")
    yandex_page_limit = request.form.get("yandex_page_limit", "9")
    google_page_limit = request.form.get("google_page_limit", "10")
    device = "desktop"  # Устанавливаем значение по умолчанию

    loc_id_google = request.form.get("loc_id_google")
    loc_id_yandex = request.form.get("loc_id_yandex")

    if engine == "google":
        try:
            loc_id = (
                int(loc_id_google)
                if loc_id_google and loc_id_google != "undefined"
                else 20949
            )
            depth = int(google_page_limit)
        except (ValueError, TypeError):
            depth = 10
    else:
        try:
            loc_id = (
                int(loc_id_yandex)
                if loc_id_yandex and loc_id_yandex != "undefined"
                else 213
            )
            depth = int(yandex_page_limit)
        except (ValueError, TypeError):
            depth = 9

    mode = MODE

    session_id = f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    logger.info(
        f"[{session_id}] Данные формы: engine={engine}, yandex_type={yandex_type}, queries_len={len(queries)}, domain={domain}, loc_id_google={loc_id_google}, loc_id_yandex={loc_id_yandex}"
    )
    logger.info(
        f"[{session_id}] Расчетные параметры: loc_id={loc_id}, depth={depth}, yandex_page_limit={yandex_page_limit}, google_page_limit={google_page_limit}"
    )

    print(f"Парсинг Топа ({session_id}): {engine}")
    print(f"Парсинг Топа: {yandex_type}")
    print(f"Парсинг Топа: {queries}")
    print(f"Локация: {loc_id}")

    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            insert_query = """
            INSERT INTO parsing_sessions (session_id, domain, engine, user_id, region, device, depth, yandex_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(
                insert_query,
                (
                    session_id,
                    domain,
                    engine,
                    current_user.id,
                    loc_id,
                    device,
                    depth,
                    yandex_type if engine == "yandex" else None,
                ),
            )
            connection.commit()
            cursor.close()
            connection.close()
        else:
            return "Ошибка при создании сессии парсинга"
    except Error as e:
        logger.error(f"Ошибка создания сессии в базе данных: {e}", exc_info=True)
        return "Ошибка при создании сессии парсинга"

    logger.info(f"Запуск потока парсинга для сессии {session_id}")
    thread = threading.Thread(
        target=run_parsing_in_thread,
        args=(
            engine,
            queries,
            domain,
            mode,
            session_id,
            current_user.id,
            yandex_type,
            yandex_page_limit,
            google_page_limit,
            loc_id,
        ),
    )
    thread.start()

    return jsonify(
        {"status": "started", "message": "Парсинг запущен", "session_id": session_id}
    )


@parsing_routes.route("/status")
@login_required
def get_status():
    global parsing_status

    # Получаем текущую сессию, если она есть
    session_id = parsing_status.get("session_id")
    spent_limits = 0

    if session_id:
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute(
                    "SELECT spent_limits FROM parsing_sessions WHERE session_id = %s",
                    (session_id,),
                )
                result = cursor.fetchone()
                if result and result["spent_limits"] is not None:
                    spent_limits = result["spent_limits"]
                cursor.close()
                connection.close()
        except Error as e:
            logger.error(
                f"Ошибка получения spent_limits для сессии {session_id}: {e}",
                exc_info=True,
            )

    # Копируем статус и добавляем/обновляем spent_limits
    status_response = parsing_status.copy()
    status_response["spent_limits"] = spent_limits

    return jsonify(status_response)


@parsing_routes.route("/download-session-results/<session_id>")
@login_required
def download_session_results(session_id):
    from flask import send_file

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM parsing_sessions WHERE session_id = %s AND user_id = %s",
            (session_id, current_user.id),
        )
        session_data = cursor.fetchone()
        cursor.close()
        conn.close()

        if not session_data:
            flash("У вас нет доступа к этой сессии", "danger")
            return redirect(url_for("main.show_results"))
    else:
        flash("Ошибка подключения к базе данных", "danger")
        return redirect(url_for("main.show_results"))

    format_type = request.args.get("format", "xlsx")

    results = get_results_from_db(session_id)

    if not results:
        return "Нет данных для скачивания", 404

    if format_type == "txt":
        output = io.StringIO()
        for result in results:
            output.write(f"Запрос: {result.get('query', result.get('Query', ''))}\n")
            output.write(
                f"Позиция: {result.get('position', result.get('Position', ''))}\n"
            )
            output.write(f"URL: {result.get('url', result.get('URL', ''))}\n")
            output.write(
                f"Статус: {result.get('processed', result.get('Processed', ''))}\n"
            )
            output.write("---\n")

        txt_content = output.getvalue()
        output.close()

        return Response(
            txt_content,
            mimetype="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename=session_{session_id}.txt"
            },
        )

    elif format_type == "csv_utf8" or format_type == "csv_win1251":
        encoding = "utf-8" if format_type == "csv_utf8" else "windows-1251"
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["Запрос", "Позиция", "URL", "Статус"])

        for result in results:
            row = [
                result.get("query", result.get("Query", "")),
                result.get("position", result.get("Position", "")),
                result.get("url", result.get("URL", "")),
                result.get("processed", result.get("Processed", "")),
            ]
            writer.writerow(row)

        csv_content = output.getvalue()
        output.close()

        return Response(
            csv_content.encode(encoding),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=session_{session_id}_{encoding}.csv"
            },
        )

    else:  # xlsx по умолчанию
        data = []
        for result in results:
            data.append(
                {
                    "Запрос": result.get("query", result.get("Query", "")),
                    "Позиция": result.get("position", result.get("Position", "")),
                    "URL": result.get("url", result.get("URL", "")),
                    "Статус": result.get("processed", result.get("Processed", "")),
                }
            )

        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Results")

        output.seek(0)

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"session_{session_id}.xlsx",
        )


@parsing_routes.route("/delete-session/<session_id>", methods=["DELETE"])
@login_required
def delete_session(session_id):
    try:
        connection = create_connection()
        if not connection:
            return (
                jsonify(
                    {"status": "error", "message": "Ошибка подключения к базе данных"}
                ),
                500,
            )

        cursor = connection.cursor()

        cursor.execute(
            "SELECT user_id FROM parsing_sessions WHERE session_id = %s", (session_id,)
        )
        session_owner = cursor.fetchone()

        if not session_owner:
            cursor.close()
            connection.close()
            return jsonify({"status": "error", "message": "Сессия не найдена"}), 404

        if session_owner[0] != current_user.id:
            cursor.close()
            connection.close()
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "У вас нет прав на удаление этой сессии",
                    }
                ),
                403,
            )

        delete_query = (
            "DELETE FROM parsing_sessions WHERE session_id = %s AND user_id = %s"
        )
        cursor.execute(delete_query, (session_id, current_user.id))

        if cursor.rowcount == 0:
            cursor.close()
            connection.close()
            return (
                jsonify(
                    {"status": "error", "message": "Сессия не найдена или уже удалена"}
                ),
                404,
            )

        connection.commit()

        cursor.close()
        connection.close()

        return jsonify(
            {
                "status": "success",
                "message": "Сессия и все связанные данные успешно удалены",
            }
        )

    except Error as e:
        logger.error(
            f"Ошибка базы данных при удалении сессии {session_id}: {e}", exc_info=True
        )
        if "connection" in locals() and connection.is_connected():
            connection.rollback()
        return (
            jsonify(
                {"status": "error", "message": "Ошибка базы данных при удалении сессии"}
            ),
            500,
        )
    except Exception as e:
        logger.error(
            f"Непредвиденная ошибка при удалении сессии {session_id}: {e}",
            exc_info=True,
        )
        return jsonify({"status": "error", "message": "Внутренняя ошибка сервера"}), 500
    finally:
        if "cursor" in locals() and cursor:
            cursor.close()
        if "connection" in locals() and connection.is_connected():
            connection.close()


# @parsing_routes.route('/start-top-sites-parsing', methods=['POST'])
# @login_required
# def start_top_sites_parsing():
#     try:
#         # queries_text = request.form.get('queries')
#         queries_list = request.form.getlist('queries')
#         search_engine = request.form.get('search_engine')
#         # region = request.form.get('region') # Это поле больше не используется напрямую
#         device = request.form.get('device')
#         depth_str = request.form.get('depth')
#         depth = int(depth_str) if depth_str and depth_str.isdigit() else 1
#         yandex_type = request.form.get('yandex_type', 'search_api')

#         yandex_page_limit_str = request.form.get('yandex_page_limit')
#         yandex_page_limit = int(yandex_page_limit_str) if yandex_page_limit_str and yandex_page_limit_str.isdigit() else 1

#         google_page_limit_str = request.form.get('google_page_limit')
#         google_page_limit = int(google_page_limit_str) if google_page_limit_str and google_page_limit_str.isdigit() else 1
#         # Determine which loc_id to use
#         # loc_id теперь передается как единое поле, не зависимо от поисковика
#         loc_id_str = request.form.get('loc_id')
#         if loc_id_str and loc_id_str != 'undefined':
#             loc_id = int(loc_id_str)
#         else:
#             # Если loc_id не предоставлен или 'undefined', используем значение по умолчанию
#             loc_id = 213 if request.form.get('search_engine') == 'yandex' else 20949

#         user_id = current_user.id
#         # Объединяем список фраз обратно в текст, разделенный новой строкой, если это необходимо для дальнейшей обработки
#         queries_text = '\n'.join(queries_list)
#         logger.info(f"Запуск парсинга ТОП-10. Движок: {search_engine}, Тип Яндекса: {yandex_type}, Глубина: {depth}, Лимит страниц Yandex: {yandex_page_limit}, Лимит страниц Google: {google_page_limit}, Локация: {loc_id}")
#         logger.debug(f"Параметры парсинга ТОП-10: queries_list={queries_list}, search_engine={search_engine}, device={device}, depth={depth}, yandex_type={yandex_type}, yandex_page_limit={yandex_page_limit}, google_page_limit={google_page_limit}, loc_id={loc_id}")

#         queries = [q.strip() for q in queries_list if q.strip()]
#         if not all([queries, search_engine, loc_id, device]):
#             return jsonify({"error": "Отсутствуют обязательные параметры."}), 400

#         # --- Проверка лимитов (основная логика вынесена в /estimate-limits) ---
#         # Оставляем проверку на сервере для безопасности
#         required_limits = 0
#         queries_count = len(queries)
#         if search_engine == 'yandex' and yandex_type == 'search_api':
#             required_limits = queries_count
#         else:
#             page_limit = google_page_limit if search_engine == 'google' else yandex_page_limit
#             required_limits = queries_count * page_limit

#         if current_user.limits < required_limits:
#             return jsonify({
#                 "error": f"Недостаточно лимитов для выполнения задачи. Требуется: {required_limits}, у вас в наличии: {current_user.limits}."
#             }), 400
#         # --- Конец проверки ---

#         connection = create_connection()
#         if not connection:
#             return jsonify({"error": "Не удалось подключиться к базе данных."}), 500

#         cursor = connection.cursor()

#         task_sql = """
#         INSERT INTO top_sites_tasks (user_id, search_engine, region, device, depth, status, yandex_type)
#         VALUES (%s, %s, %s, %s, %s, 'running', %s)
#         """
#         cursor.execute(task_sql, (user_id, search_engine, loc_id, device, depth, yandex_type if search_engine == 'yandex' else None))
#         task_id = cursor.lastrowid

#         queries_to_process = []
#         for query_text in queries:
#             query_sql = "INSERT INTO top_sites_queries (task_id, query_text) VALUES (%s, %s) "
#             cursor.execute(query_sql, (task_id, query_text))
#             query_id = cursor.lastrowid
#             queries_to_process.append({'id': query_id, 'text': query_text})

#         connection.commit()

#         thread = threading.Thread(
#             target=run_top_sites_parsing_thread,
#             args=(task_id, queries_to_process, search_engine, loc_id, device, depth, yandex_type, yandex_page_limit, google_page_limit, user_id)
#         )
#         thread.start()

#         return jsonify({
#             "status": "success",
#             "message": f"Задача парсинга ТОП-10 запущена для {len(queries)} фраз. Будет списано примерно {required_limits} лимитов.",
#             "task_id": task_id
#         })

#     except Exception as e:
#         logger.error(f"Ошибка при запуске задачи парсинга ТОП-10: {e}", exc_info=True)
#         if 'connection' in locals() and connection.is_connected():
#             connection.rollback()
#         return jsonify({"error": "Внутренняя ошибка сервера при запуске задачи."}), 500
#     finally:
#         if 'cursor' in locals():
#             cursor.close()
#         if 'connection' in locals() and connection.is_connected():
#             connection.close()

# @parsing_routes.route('/estimate-limits', methods=['POST'])
# @login_required
# def estimate_limits():
#    """
#    Оценивает и возвращает необходимое количество лимитов для задачи парсинга.
#    """
#    try:
#        logger.debug(f"Запрос на оценку лимитов. Request form: {request.form}")
#        # Данные приходят как form-data, а не JSON. Используем request.form.
#        # request.form.getlist используется для получения всех значений с одинаковым именем,
#        # на случай если фронтенд будет отправлять несколько полей 'queries'.
#        queries_list = request.form.getlist('queries')
#        search_engine = request.form.get('search_engine')
#        yandex_type = request.form.get('yandex_type', 'search_api')
#        yandex_page_limit = int(request.form.get('yandex_page_limit', 1))
#        google_page_limit = int(request.form.get('google_page_limit', 1))

#        queries = [q.strip() for q in queries_list if q.strip()]
#        if not queries:
#            return jsonify({"error": "Список запросов пуст."}), 400

#        # --- Логика прогнозирования лимитов ---
#        required_limits = 0
#        queries_count = len(queries)

#        if search_engine == 'yandex' and yandex_type == 'search_api':
#            required_limits = queries_count
#        else:  # Live Search или Google
#            page_limit = google_page_limit if search_engine == 'google' else yandex_page_limit
#            required_limits = queries_count * page_limit

#        return jsonify({
#            "estimated_limits": required_limits,
#            "available_limits": current_user.limits
#        })

#    except Exception as e:
#        logger.error(f"Ошибка при оценке лимитов: {e}", exc_info=True)
#        return jsonify({"error": "Внутренняя ошибка сервера при оценке лимитов."}), 500

# @parsing_routes.route('/estimate-limits-parser', methods=['POST'])
# @login_required
# def estimate_limits_parser():
#   """
#   Оценивает и возвращает необходимое количество лимитов для задачи парсинга позиций.
#   """
#   try:
#       logger.debug(f"Запрос на оценку лимитов парсера. Request form: {request.form}")
#       queries_text = request.form.get('queries', '')
#       engine = request.form.get('engine')
#       yandex_type = request.form.get('yandex_type', 'search_api')
#       yandex_page_limit = int(request.form.get('yandex_page_limit', 1))
#       google_page_limit = int(request.form.get('google_page_limit', 1))

#       queries = [q.strip() for q in queries_text.splitlines() if q.strip()]
#       if not queries:
#           return jsonify({"error": "Список запросов пуст."}), 400

#       required_limits = 0
#       queries_count = len(queries)

#       if engine == 'yandex' and yandex_type == 'search_api':
#           required_limits = queries_count
#       else:  # Live Search или Google
#           page_limit = google_page_limit if engine == 'google' else yandex_page_limit
#           required_limits = queries_count * page_limit

#       return jsonify({
#           "estimated_limits": required_limits,
#           "available_limits": current_user.limits
#       })

#   except Exception as e:
#       logger.error(f"Ошибка при оценке лимитов парсера: {e}", exc_info=True)
#       return jsonify({"error": "Внутренняя ошибка сервера при оценке лимитов."}), 500

# @parsing_routes.route("/download-top-sites/<int:task_id>")
# @login_required
# def download_top_sites_task(task_id):
#     from flask import send_file

#     format_type = request.args.get('format', 'xlsx')

#     connection = create_connection()
#     if not connection:
#         flash("Ошибка подключения к базе данных.", "danger")
#         return redirect(url_for('top_sites.top_sites_page'))

#     try:
#         cursor = connection.cursor(dictionary=True)

#         cursor.execute("SELECT * FROM top_sites_tasks WHERE id = %s AND user_id = %s", (task_id, current_user.id))
#         task_info = cursor.fetchone()

#         if not task_info:
#             flash("Задача не найдена или у вас нет к ней доступа.", "danger")
#             return redirect(url_for('top_sites.top_sites_page'))

#         cursor.execute("SELECT * FROM top_sites_queries WHERE task_id = %s", (task_id,))
#         first_query = cursor.fetchone()
#         first_query_text = first_query['query_text'].replace(" ", "_") if first_query else ""

#         # Получаем имя региона
#         region_name = get_region_name_by_id(task_info.get('search_engine'), task_info.get('region'))


#         # Формируем имя файла
#         filename_parts = [
#             f"Задача_{task_id}",
#             task_info['search_engine'],
#         ]
#         if task_info.get('yandex_type'):
#             filename_parts.append(task_info['yandex_type'])

#         filename_parts.extend([
#             region_name,
#             task_info['device'],
#             task_info['created_at'].strftime('%Y-%m-%d'),
#             first_query_text
#         ])

#         base_filename = "_".join(filter(None, filename_parts))

#         sql = """
#         SELECT tq.query_text, tr.position, tr.url
#         FROM top_sites_results tr
#         JOIN top_sites_queries tq ON tr.query_id = tq.id
#         WHERE tq.task_id = %s
#         ORDER BY tq.id, tr.position ASC
#         """
#         cursor.execute(sql, (task_id,))
#         results = cursor.fetchall()

#         if not results:
#             flash("Нет данных для скачивания по этой задаче.", "warning")
#             return redirect(url_for('top_sites.top_sites_page'))

#         if format_type == 'csv_utf8' or format_type == 'csv_win1251':
#             encoding = 'utf-8' if format_type == 'csv_utf8' else 'windows-1251'
#             output = io.StringIO()
#             writer = csv.writer(output)

#             writer.writerow(['Запрос', 'Позиция', 'URL'])

#             for res in results:
#                 writer.writerow([res['query_text'], res['position'], res['url']])

#             csv_content = output.getvalue()
#             output.close()

#             return send_file(
#                 io.BytesIO(csv_content.encode(encoding)),
#                 mimetype="text/csv",
#                 as_attachment=True,
#                 download_name=f"{base_filename}.csv"
#             )
#         elif format_type == 'txt':
#             output = io.StringIO()
#             current_query = None
#             for res in results:
#                 if res['query_text'] != current_query:
#                     current_query = res['query_text']
#                     output.write(f"\n--- Результаты для запроса: {current_query} ---\n")
#                 output.write(f"{res['position']}. {res['url']}\n")

#             output.seek(0)
#             return send_file(
#                 io.BytesIO(output.getvalue().encode('utf-8')),
#                 mimetype="text/plain",
#                 as_attachment=True,
#                 download_name=f"{base_filename}.txt"
#             )
#         else: # xlsx по умолчанию
#             df = pd.DataFrame(results, columns=['query_text', 'position', 'url'])
#             df.rename(columns={'query_text': 'Запрос', 'position': 'Позиция', 'url': 'URL'}, inplace=True)

#             output = io.BytesIO()
#             with pd.ExcelWriter(output, engine='openpyxl') as writer:
#                 df.to_excel(writer, index=False, sheet_name=f'Task_{task_id}')
#             output.seek(0)

#             return send_file(
#                 output,
#                 mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#                 as_attachment=True,
#                 download_name=f"{base_filename}.xlsx"
#             )

#     except Error as e:
#         logger.error(f"Ошибка базы данных при скачивании результатов задачи {task_id}: {e}", exc_info=True)
#         flash("Ошибка базы данных при формировании файла.", "danger")
#         return redirect(url_for('top_sites.top_sites_page'))
#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()

# @parsing_routes.route("/delete-top-sites/<int:task_id>", methods=["DELETE"])
# @login_required
# def delete_top_sites_task(task_id):
#     connection = create_connection()
#     if not connection:
#         return jsonify({"status": "error", "message": "Ошибка подключения к базе данных."}), 500

#     try:
#         cursor = connection.cursor()

#         cursor.execute("SELECT user_id FROM top_sites_tasks WHERE id = %s", (task_id,))
#         task = cursor.fetchone()
#         if not task or task[0] != current_user.id:
#             return jsonify({"status": "error", "message": "У вас нет прав на удаление этой задачи."}), 403

#         cursor.execute("DELETE FROM top_sites_tasks WHERE id = %s", (task_id,))
#         connection.commit()

#         return jsonify({"status": "success", "message": "Задача и все связанные данные успешно удалены."})

#     except Error as e:
#         logger.error(f"Ошибка базы данных при удалении задачи {task_id}: {e}", exc_info=True)
#         return jsonify({"status": "error", "message": "Ошибка базы данных при удалении."}), 500
#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()
