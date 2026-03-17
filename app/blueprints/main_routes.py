"""
Main routes blueprint for SERP bot application.

Contains core application routes such as:
- Home page
- Results page
- Balance checking
- Import pages
- Session management
"""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    Response,
)
from flask_login import login_required, current_user
import os
import logging
import io
import csv
import pandas as pd
from ..config import MODE
from ..db.settings_db import get_setting
from ..db.database import (
    get_db_connection,
    get_user_sessions_from_db,
    get_results_from_db,
    update_session_status,
    spend_limit,
    execute_sql_from_file,
)
from ..parsing import parsing_status
from mysql.connector import Error
import import_locations

from ..db_config import LOGGING_ENABLED

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "main_routes.log")
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

# Импортируем наш новый парсер частотности
from app.keyword_frequency_parser import KeywordFrequencyParser, FrequencyType

from app.services.dashboard_service import DashboardService

main_routes = Blueprint("main", __name__)


@main_routes.context_processor
def inject_user():
    """
    Внедряет информацию о текущем пользователе во все шаблоны,
    связанные с этим blueprint. Это позволяет получить доступ к
    `current_user` в базовом шаблоне `layout.html` и других.
    """
    return dict(current_user=current_user)


@main_routes.route("/keyword-frequency", methods=["GET", "POST"])
@login_required
def keyword_frequency():
    """
    Страница для получения частотности ключевых слов.
    """
    if LOGGING_ENABLED:
        logger.info(
            f"Пользователь {current_user.username} (ID: {current_user.id}) открыл страницу частотности."
        )

    result = {}
    if request.method == "POST":
        keyword = request.form.get("keyword", "").strip()
        if keyword:
            try:
                parser = KeywordFrequencyParser()

                # Получаем частотности для Яндекса
                result["yandex_basic"] = parser.get_frequency(
                    keyword, FrequencyType.YANDEX_BASIC
                )
                result["yandex_phrase"] = parser.get_frequency(
                    keyword, FrequencyType.YANDEX_PHRASE
                )
                result["yandex_exact"] = parser.get_frequency(
                    keyword, FrequencyType.YANDEX_EXACT
                )

                # Заглушка для Google
                result["google_basic"] = parser.get_frequency(
                    keyword, FrequencyType.GOOGLE_BASIC
                )
                result["google_refined"] = parser.get_frequency(
                    keyword, FrequencyType.GOOGLE_REFINED
                )

                result["keyword"] = keyword

                if LOGGING_ENABLED:
                    logger.info(f"Частотности для '{keyword}' получены: {result}")

            except ValueError as e:
                # Ошибка при инициализации парсера (например, нет API ключа)
                if LOGGING_ENABLED:
                    logger.error(f"Ошибка инициализации парсера частотности: {e}")
                flash(str(e), "error")
                result = {}

    return render_template("keyword_frequency.html", result=result)


@main_routes.route("/")
def index():
    try:
        if current_user.is_authenticated:
            stats = DashboardService.get_stats(current_user.id)
            activity = DashboardService.get_recent_activity(current_user.id)
            return render_template("index.html", stats=stats, activity=activity)
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Ошибка рендеринга шаблона index.html: {e}", exc_info=True)
        return f"Ошибка рендеринга шаблона: {str(e)}"


@main_routes.route("/quick-check")
def quick_check():
    # def index():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    try:
        sessions = get_user_sessions_from_db(current_user.id)
        max_queries = int(get_setting("MAX_QUERIES") or 5)
        return render_template(
            "quick-check.html", sessions=sessions, max_queries=max_queries
        )
    except Exception as e:
        logger.error(f"Ошибка рендеринга шаблона quick-check.html: {e}", exc_info=True)
        return f"Ошибка рендеринга шаблона: {str(e)}"


@main_routes.route("/show-results")
@login_required
def show_results():
    session_id = request.args.get("session_id")

    if session_id:
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

        if parsing_status["error"]:
            return f"<h2>Ошибка:</h2><p>{parsing_status['error']}</p><a href='/'>Вернуться на главную</a>"

        results = get_results_from_db(session_id)

        positions = [
            int(r["position"])
            for r in results
            if r["position"] and r["position"] != "-"
        ]
        if positions:
            avg_position = sum(positions) / len(positions)
            top_10 = len([p for p in positions if p <= 10])
        else:
            avg_position = 0
            top_10 = 0

        all_sessions = get_user_sessions_from_db(current_user.id)
        return render_template(
            "results.html",
            results=results,
            avg_position=avg_position,
            top_10=top_10,
            session_id=session_id,
            sessions=all_sessions,
            session_info=session_data,
        )

    else:
        sessions = get_user_sessions_from_db(current_user.id)
        return render_template("results.html", sessions=sessions)


@main_routes.route("/get-balance")
@login_required
def get_balance():
    try:
        api_url = os.getenv("API_KEY")
        if not api_url:
            raise ValueError("API_KEY не найден в .env")

        from urllib.parse import urlparse, parse_qs

        parsed_url = urlparse(api_url)
        query_params = parse_qs(parsed_url.query)
        user = query_params.get("user", [None])[0]
        key = query_params.get("key", [None])[0]

        if not user or not key:
            raise ValueError("Не удалось извлечь user или key из API_KEY")

        balance_url = "https://xmlriver.com/api/get_balance/"
        params = {"user": user, "key": key}

        import requests

        response = requests.get(balance_url, params=params)
        response.raise_for_status()

        return jsonify({"balance": response.text.strip()})

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса к API баланса: {e}", exc_info=True)
        return jsonify({"error": f"Ошибка запроса к API: {e}"}), 500
    except ValueError as e:
        logger.error(f"Ошибка значения при получении баланса: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении баланса: {e}", exc_info=True)
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500


@main_routes.route("/import-locations")
@login_required
def import_locations_page():
    """Отображает страницу для запуска импорта локаций."""
    return render_template("import.html")


@main_routes.route("/run-import-locations", methods=["POST"])
@login_required
def run_import_locations():
    """Запускает импорт локаций из CSV файла."""
    try:
        import threading

        # Путь к файлу geo (1).csv относительно корня проекта
        filepath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "geo (1).csv"
        )

        # Запускаем импорт в отдельном потоке, чтобы не блокировать основной процесс
        thread = threading.Thread(
            target=import_locations.import_locations_from_csv, args=(filepath,)
        )
        thread.start()

        flash(
            "Процесс импорта запущен в фоновом режиме. Это может занять некоторое время.",
            "info",
        )
    except Exception as e:
        logger.error(f"Ошибка при запуске потока импорта: {e}", exc_info=True)
        flash(f"Произошла ошибка при запуске импорта: {e}", "danger")

    return redirect(url_for("main.import_locations_page"))


@main_routes.route("/import-yandex-regions")
@login_required
def yandex_regions_import_page():
    """Отображает страницу для запуска импорта регионов Яндекса."""
    return render_template("yandex_regions_import.html")


@main_routes.route("/run-yandex-regions-import", methods=["POST"])
@login_required
def run_yandex_regions_import():
    """Запускает выполнение SQL-скрипта для создания и заполнения таблицы регионов Яндекса."""
    try:
        filepath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "yandex_regions.sql"
        )
        success, message = execute_sql_from_file(filepath)
        if success:
            flash(message, "success")
        else:
            flash(message, "danger")
    except Exception as e:
        logger.error(f"Ошибка при запуске импорта регионов Яндекса: {e}", exc_info=True)
        flash(f"Произошла ошибка при запуске импорта: {e}", "danger")

    return redirect(url_for("main.yandex_regions_import_page"))


# @main_routes.route("/download-session-results/<session_id>")
# @login_required
# def download_session_results(session_id):
#     from flask import send_file

#     conn = get_db_connection()
#     if conn:
#         cursor = conn.cursor(dictionary=True)
#         cursor.execute(
#             "SELECT * FROM parsing_sessions WHERE session_id = %s AND user_id = %s",
#             (session_id, current_user.id)
#         )
#         session_data = cursor.fetchone()
#         cursor.close()
#         conn.close()

#         if not session_data:
#             flash("У вас нет доступа к этой сессии", "danger")
#             return redirect(url_for('main.show_results'))
#     else:
#         flash("Ошибка подключения к базе данных", "danger")
#         return redirect(url_for('main.show_results'))

#     format_type = request.args.get('format', 'xlsx')

#     results = get_results_from_db(session_id)

#     if not results:
#         return "Нет данных для скачивания", 404

#     if format_type == 'txt':
#         output = io.StringIO()
#         for result in results:
#             output.write(f"Запрос: {result.get('query', result.get('Query', ''))}\n")
#             output.write(f"Позиция: {result.get('position', result.get('Position', ''))}\n")
#             output.write(f"URL: {result.get('url', result.get('URL', ''))}\n")
#             output.write(f"Статус: {result.get('processed', result.get('Processed', ''))}\n")
#             output.write("---\n")

#         txt_content = output.getvalue()
#         output.close()

#         return Response(
#             txt_content,
#             mimetype="text/plain",
#             headers={"Content-Disposition": f"attachment; filename=session_{session_id}.txt"}
#         )

#     elif format_type == 'csv_utf8' or format_type == 'csv_win1251':
#         encoding = 'utf-8' if format_type == 'csv_utf8' else 'windows-1251'
#         output = io.StringIO()
#         writer = csv.writer(output)

#         writer.writerow(['Запрос', 'Позиция', 'URL', 'Статус'])

#         for result in results:
#             row = [
#                 result.get('query', result.get('Query', '')),
#                 result.get('position', result.get('Position', '')),
#                 result.get('url', result.get('URL', '')),
#                 result.get('processed', result.get('Processed', ''))
#             ]
#             writer.writerow(row)

#         csv_content = output.getvalue()
#         output.close()

#         return Response(
#             csv_content.encode(encoding),
#             mimetype="text/csv",
#             headers={"Content-Disposition": f"attachment; filename=session_{session_id}_{encoding}.csv"}
#         )

#     else:  # xlsx по умолчанию
#         data = []
#         for result in results:
#             data.append({
#                 'Запрос': result.get('query', result.get('Query', '')),
#                 'Позиция': result.get('position', result.get('Position', '')),
#                 'URL': result.get('url', result.get('URL', '')),
#                 'Статус': result.get('processed', result.get('Processed', ''))
#             })

#         df = pd.DataFrame(data)

#         output = io.BytesIO()
#         with pd.ExcelWriter(output, engine='openpyxl') as writer:
#             df.to_excel(writer, index=False, sheet_name='Results')

#         output.seek(0)

#         return send_file(
#             output,
#             mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#             as_attachment=True,
#             download_name=f"session_{session_id}.xlsx"
#         )

# @main_routes.route("/delete-session/<session_id>", methods=["DELETE"])
# @login_required
# def delete_session(session_id):
#     try:
#         connection = get_db_connection()
#         if not connection:
#             return jsonify({'status': 'error', 'message': 'Ошибка подключения к базе данных'}), 500

#         cursor = connection.cursor()

#         cursor.execute(
#             "SELECT user_id FROM parsing_sessions WHERE session_id = %s",
#             (session_id,)
#         )
#         session_owner = cursor.fetchone()

#         if not session_owner:
#             cursor.close()
#             connection.close()
#             return jsonify({'status': 'error', 'message': 'Сессия не найдена'}), 404

#         if session_owner[0] != current_user.id:
#             cursor.close()
#             connection.close()
#             return jsonify({'status': 'error', 'message': 'У вас нет прав на удаление этой сессии'}), 403

#         delete_query = "DELETE FROM parsing_sessions WHERE session_id = %s AND user_id = %s"
#         cursor.execute(delete_query, (session_id, current_user.id))

#         if cursor.rowcount == 0:
#             cursor.close()
#             connection.close()
#             return jsonify({'status': 'error', 'message': 'Сессия не найдена или уже удалена'}), 404

#         connection.commit()

#         cursor.close()
#         connection.close()

#         return jsonify({'status': 'success', 'message': 'Сессия и все связанные данные успешно удалены'})

#     except Error as e:
#         logger.error(f"Ошибка базы данных при удалении сессии {session_id}: {e}", exc_info=True)
#         if 'connection' in locals() and connection.is_connected():
#             connection.rollback()
#         return jsonify({'status': 'error', 'message': 'Ошибка базы данных при удалении сессии'}), 500
#     except Exception as e:
#         logger.error(f"Непредвиденная ошибка при удалении сессии {session_id}: {e}", exc_info=True)
#         return jsonify({'status': 'error', 'message': 'Внутренняя ошибка сервера'}), 500
#     finally:
#         if 'cursor' in locals() and cursor:
#             cursor.close()
#         if 'connection' in locals() and connection.is_connected():
#             connection.close()
