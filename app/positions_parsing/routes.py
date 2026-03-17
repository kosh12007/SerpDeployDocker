import os
import logging
import threading
from flask import (
    Blueprint,
    render_template,
    abort,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from flask_login import login_required, current_user
from app.db.database import get_db_connection
from app.db_config import LOGGING_ENABLED
from app.config import MODE
from app.models import ParsingVariant, Query
from app.positions_parsing.core.parser import run_positions_parsing_in_thread
from app.positions_parsing.db.operations import create_parsing_positions_session
from app.positions_parsing.utils.limits import estimate_limits as new_estimate_limits
from app.positions_parsing.db.operations import get_failed_queries_for_reparse

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "positions_parsing_routes.log")
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

# Создание Blueprint для парсинга позиций
positions_parsing_bp = Blueprint(
    "positions_parsing", __name__, template_folder="templates"
)


@positions_parsing_bp.route("/projects/<int:project_id>/positions")
@login_required
def project_positions(project_id, variant_id=None):
    """
    Отображает страницу проверки позиций для проекта.
    """
    conn = None
    project = None
    queries = []
    positions = {}
    variants = []
    dates = []
    groups = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Получаем данные проекта и проверяем принадлежность пользователю
        cursor.execute(
            "SELECT * FROM projects WHERE id = %s AND user_id = %s",
            (project_id, current_user.id),
        )
        project = cursor.fetchone()

        if not project:
            abort(404)

        # 2. Получаем варианты парсинга
        from app.models import ParsingVariant

        variants_raw = ParsingVariant.get_by_project_id(project_id)

        variants = []
        for variant in variants_raw:
            details = [
                variant.search_engine,
                variant.search_type,
                variant.region or variant.location,
                variant.device,
            ]
            details_str = " / ".join(filter(None, details))

            variant.full_text = f"{variant.name} ({details_str})"
            variants.append(variant)

        if LOGGING_ENABLED:
            logger.debug(f"Найдены и отформатированы варианты: {variants}")

        # 3. Получаем запросы
        sql_queries = """
            SELECT q.*, qg.name as group_name
            FROM queries q
            LEFT JOIN query_groups qg ON q.query_group_id = qg.id
            WHERE q.project_id = %s
        """
        cursor.execute(sql_queries, (project_id,))
        queries = cursor.fetchall()

        # 4. Получаем историю позиций
        variant_id = request.args.get("variant_id", type=int)

        subquery_params = []
        subquery_sql = "SELECT query_id, parsing_variant_id, date, MAX(id) as max_id FROM parsing_position_results"
        if variant_id:
            subquery_sql += " WHERE parsing_variant_id = %s"
            subquery_params.append(variant_id)
        subquery_sql += " GROUP BY query_id, parsing_variant_id, date"

        sql_positions = f"""
            SELECT ppr.query_id, ppr.position, ppr.date, ppr.status
            FROM parsing_position_results ppr
            INNER JOIN ({subquery_sql}) AS max_results
                ON ppr.query_id = max_results.query_id
                AND ppr.parsing_variant_id = max_results.parsing_variant_id
                AND ppr.date = max_results.date
                AND ppr.id = max_results.max_id
            JOIN queries q ON ppr.query_id = q.id
            WHERE q.project_id = %s
        """

        params = subquery_params + [project_id]

        sql_positions += " ORDER BY ppr.date"

        cursor.execute(sql_positions, tuple(params))

        all_positions = cursor.fetchall()

        # Собираем все уникальные даты
        all_dates = sorted(list(set(row["date"] for row in all_positions)))

        # Преобразуем даты в строки для удобства
        dates = [d.strftime("%Y-%m-%d") for d in all_dates]

        # Реструктурируем `positions`, включая статус
        for row in all_positions:
            query_id = row["query_id"]
            date_str = row["date"].strftime("%Y-%m-%d")
            if query_id not in positions:
                positions[query_id] = {}
            positions[query_id][date_str] = {
                "position": row["position"],
                "status": row["status"],
            }

        # Собираем уникальные группы
        groups = sorted(list(set(q["group_name"] for q in queries if q["group_name"])))

        if LOGGING_ENABLED:
            logger.debug(f"Найдены позиции: {positions}")
            logger.debug(f"Даты: {dates}")
            logger.debug(f"Группы: {groups}")

        # Получаем активные задачи парсинга для этого проекта
        active_sessions = []
        try:
            cursor.execute(
                """
                SELECT id, status, created_at, spent_limits
                FROM parsing_positions_sessions
                WHERE project_id = %s AND user_id = %s 
                AND status IN ('pending', 'in_progress')
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (project_id, current_user.id),
            )
            active_sessions = cursor.fetchall()
        except Exception as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка при получении активных сессий для проекта {project_id}: {e}",
                    exc_info=True,
                )

    finally:
        if conn and conn.is_connected():
            if "cursor" in locals():
                cursor.close()
            conn.close()

    return render_template(
        "projects/project_positions.html",
        project=project,
        queries=queries,
        positions=positions,
        variants=variants,
        dates=dates,
        groups=groups,
        active_session=active_sessions[0] if active_sessions else None,
    )


@positions_parsing_bp.route(
    "/api/projects/<int:project_id>/estimate-limits", methods=["GET"]
)
@login_required
def estimate_limits(project_id):
    """
    Рассчитывает и возвращает предполагаемую стоимость парсинга,
    количество запросов и текущий баланс пользователя.
    """
    variant_id = request.args.get("variant_id", type=int)
    if not variant_id:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Необходим ID варианта парсинга (variant_id).",
                }
            ),
            400,
        )

        # Проверяем владение проектом
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id FROM projects WHERE id = %s AND user_id = %s",
            (project_id, current_user.id),
        )
        project_check = cursor.fetchone()
        cursor.close()
        conn.close()

        if not project_check:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Проект не найден или у вас нет доступа.",
                    }
                ),
                404,
            )

    estimated_cost, queries_count = new_estimate_limits(variant_id, project_id)

    if queries_count == 0 and estimated_cost == 0:
        variant = ParsingVariant.get_by_id(variant_id)
        if not variant:
            return (
                jsonify({"success": False, "message": "Вариант парсинга не найден."}),
                404,
            )

    # 4. Получаем баланс пользователя
    user_balance = current_user.limits if current_user.limits is not None else 0

    return jsonify(
        {
            "success": True,
            "estimated_cost": estimated_cost,
            "user_balance": user_balance,
            "queries_count": queries_count,
        }
    )


@positions_parsing_bp.route(
    "/api/projects/<int:project_id>/estimate-retry-limits", methods=["GET"]
)
@login_required
def estimate_retry_limits(project_id):
    """
    Рассчитывает предполагаемую стоимость повторного парсинга для ошибочных запросов.
    """
    variant_id = request.args.get("variant_id", type=int)
    if not variant_id:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Необходим ID варианта парсинга (variant_id).",
                }
            ),
            400,
        )

    # Проверяем владение проектом
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id FROM projects WHERE id = %s AND user_id = %s",
        (project_id, current_user.id),
    )
    project_check = cursor.fetchone()
    cursor.close()
    conn.close()

    if not project_check:
        return (
            jsonify(
                {"success": False, "message": "Проект не найден или у вас нет доступа."}
            ),
            404,
        )

    # 1. Получаем список ошибочных запросов
    failed_queries = get_failed_queries_for_reparse(variant_id, project_id)
    queries_count = len(failed_queries)

    if queries_count == 0:
        return jsonify(
            {
                "success": True,
                "estimated_cost": 0,
                "user_balance": (
                    current_user.limits if current_user.limits is not None else 0
                ),
                "queries_count": 0,
            }
        )

    # 2. Рассчитываем стоимость
    # Предполагаем, что стоимость одного запроса - 1 лимит.
    # В будущем можно будет усложнить логику, если потребуется.
    estimated_cost = queries_count

    # 3. Получаем баланс пользователя
    user_balance = current_user.limits if current_user.limits is not None else 0

    return jsonify(
        {
            "success": True,
            "estimated_cost": estimated_cost,
            "user_balance": user_balance,
            "queries_count": queries_count,
        }
    )


@positions_parsing_bp.route(
    "/api/projects/<int:project_id>/parse-positions", methods=["POST"]
)
@login_required
def parse_positions(project_id):
    """
    Запускает парсинг позиций для указанного проекта и варианта.
    """
    data = request.get_json()
    if not data or "variant_id" not in data:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Необходим ID варианта парсинга (variant_id).",
                }
            ),
            400,
        )

    variant_id = data.get("variant_id")

    if not variant_id:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Необходим ID варианта парсинга (variant_id).",
                }
            ),
            400,
        )

    # 1. Получаем вариант парсинга, чтобы получить его параметры
    variant = ParsingVariant.get_by_id(variant_id)
    if not variant:
        return (
            jsonify({"success": False, "message": "Вариант парсинга не найден."}),
            404,
        )

    # Убедимся, что у варианта есть детали типа поиска (search_type_details)
    # if not hasattr(variant, 'search_type_details') or not variant.search_type_details:
    #     return jsonify({'success': False, 'message': 'Детали типа поиска для варианта не найдены.'}), 500

    # 2. Получаем все запросы для проекта
    queries_obj = Query.get_by_project_id(project_id)
    if not queries_obj:
        return (
            jsonify(
                {"success": False, "message": "Для этого проекта не найдено запросов."}
            ),
            404,
        )

    queries_texts = "\n".join([q.query_text for q in queries_obj])

    # 3. Получаем URL проекта и проверяем принадлежность пользователю
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT url FROM projects WHERE id = %s AND user_id = %s",
        (project_id, current_user.id),
    )
    project_url_result = cursor.fetchone()
    if not project_url_result:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Проект не найден."}), 404
    project_url = project_url_result["url"]
    cursor.close()
    conn.close()

    # 4. Создаем сессию парсинга
    session_id = create_parsing_positions_session(
        user_id=current_user.id, project_id=project_id, variant_id=variant_id
    )
    if not session_id:
        return (
            jsonify(
                {"success": False, "message": "Ошибка при создании сессии парсинга."}
            ),
            500,
        )

    # 5. Запускаем парсинг в отдельном потоке
    try:
        from app.positions_parsing.core.parser import get_engine_name

        # Преобразуем search_engine_id в API-имя (api_name)
        # Используем search_engine_id вместо search_engine, так как search_engine содержит name (кириллица)
        engine_api_name = get_engine_name(variant.search_engine_id)
        parsing_thread = threading.Thread(
            target=run_positions_parsing_in_thread,
            kwargs={
                "engine": engine_api_name,
                "queries": queries_texts,
                "domain": project_url,
                "mode": MODE,
                "session_id": session_id,
                "user_id": current_user.id,
                "project_id": project_id,
                # Используем api_parameter из деталей типа поиска
                "yandex_type": (
                    variant.search_type_details.get("api_parameter")
                    if engine_api_name == "yandex"
                    else None
                ),
                "yandex_page_limit": variant.page_limit,
                "google_page_limit": variant.page_limit,
            },
        )
        parsing_thread.start()
    except Exception as e:
        # Если поток не стартовал, откатываем сессию и возвращаем ошибку
        from app.positions_parsing.db.operations import update_position_session_status

        update_position_session_status(session_id, "error")
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при запуске потока парсинга для сессии {session_id}: {e}",
                exc_info=True,
            )
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Ошибка при запуске фонового процесса парсинга.",
                }
            ),
            500,
        )

    return jsonify({"success": True, "task_id": session_id})


@positions_parsing_bp.route(
    "/api/projects/<int:project_id>/retry-failed-positions", methods=["POST"]
)
@login_required
def retry_failed_positions(project_id):
    """
    Запускает повторный парсинг для запросов, которые ранее завершились с ошибкой.
    """
    data = request.get_json()
    variant_id = data.get("variant_id")

    if not variant_id:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Необходим ID варианта парсинга (variant_id).",
                }
            ),
            400,
        )

    # 1. Получаем вариант парсинга
    variant = ParsingVariant.get_by_id(variant_id)
    if not variant:
        return (
            jsonify({"success": False, "message": "Вариант парсинга не найден."}),
            404,
        )

    # 2. Получаем список ошибочных запросов для повторного парсинга
    failed_queries = get_failed_queries_for_reparse(variant_id, project_id)
    if not failed_queries:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Не найдено запросов с ошибками для повторного парсинга.",
                }
            ),
            400,
        )

    queries_texts = "\n".join(failed_queries)

    # 3. Получаем URL проекта и проверяем принадлежность пользователю
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT url FROM projects WHERE id = %s AND user_id = %s",
        (project_id, current_user.id),
    )
    project_url_result = cursor.fetchone()
    project_url = project_url_result["url"]
    cursor.close()
    conn.close()

    # 4. Создаем новую сессию парсинга
    session_id = create_parsing_positions_session(
        user_id=current_user.id, project_id=project_id, variant_id=variant_id
    )
    if not session_id:
        return (
            jsonify(
                {"success": False, "message": "Ошибка при создании сессии парсинга."}
            ),
            500,
        )

    # 5. Запускаем парсинг в отдельном потоке
    try:
        from app.positions_parsing.core.parser import get_engine_name

        engine_api_name = get_engine_name(variant.search_engine_id)

        parsing_thread = threading.Thread(
            target=run_positions_parsing_in_thread,
            kwargs={
                "engine": engine_api_name,
                "queries": queries_texts,  # Используем только ошибочные запросы
                "domain": project_url,
                "mode": MODE,
                "session_id": session_id,
                "user_id": current_user.id,
                "project_id": project_id,
                "yandex_type": (
                    variant.search_type_details.get("api_parameter")
                    if engine_api_name == "yandex"
                    else None
                ),
                "yandex_page_limit": variant.page_limit,
                "google_page_limit": variant.page_limit,
            },
        )
        parsing_thread.start()
    except Exception as e:
        from app.positions_parsing.db.operations import update_position_session_status

        update_position_session_status(session_id, "error")
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при запуске потока повторного парсинга для сессии {session_id}: {e}",
                exc_info=True,
            )
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Ошибка при запуске фонового процесса повторного парсинга.",
                }
            ),
            500,
        )

    return jsonify({"success": True, "task_id": session_id})


@positions_parsing_bp.route("/api/parsing-status/<int:task_id>", methods=["GET"])
@login_required
def get_parsing_status(task_id):
    """
    Возвращает статус сессии парсинга позиций по её ID из таблицы parsing_positions_sessions.

    Статусы:
    - 'pending' - сессия создана, ожидает запуска
    - 'in_progress' - парсинг выполняется
    - 'completed' - парсинг завершен успешно
    - 'error' - произошла ошибка при парсинге
    - 'partial' - парсинг завершен частично
    """
    try:
        from app.positions_parsing.db.operations import get_session_info

        # Получаем информацию о сессии
        session_info = get_session_info(task_id)

        if not session_info:
            return (
                jsonify({"success": False, "message": "Сессия парсинга не найдена."}),
                404,
            )

        # Проверяем, что сессия принадлежит текущему пользователю
        if session_info.get("user_id") != current_user.id:
            return (
                jsonify(
                    {"success": False, "message": "У вас нет доступа к этой сессии."}
                ),
                403,
            )

        # Возвращаем статус и дополнительную информацию
        return jsonify(
            {
                "success": True,
                "status": session_info.get("status"),
                "spent_limits": session_info.get("spent_limits", 0),
                "created_at": (
                    session_info.get("created_at").isoformat()
                    if session_info.get("created_at")
                    else None
                ),
                "completed_at": (
                    session_info.get("completed_at").isoformat()
                    if session_info.get("completed_at")
                    else None
                ),
            }
        )

    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при получении статуса сессии {task_id}: {e}", exc_info=True
            )
        return jsonify({"success": False, "message": "Внутренняя ошибка сервера."}), 500


@positions_parsing_bp.route(
    "/api/projects/<int:project_id>/positions-data", methods=["GET"]
)
@login_required
def get_positions_data(project_id):
    """
    Возвращает данные позиций для проекта в формате JSON для AJAX-обновления таблицы.

    Используется для обновления таблицы позиций без перезагрузки страницы.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Проверяем, что проект принадлежит текущему пользователю
        cursor.execute(
            "SELECT * FROM projects WHERE id = %s AND user_id = %s",
            (project_id, current_user.id),
        )
        project = cursor.fetchone()
        if not project:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Проект не найден или у вас нет доступа.",
                    }
                ),
                404,
            )

        # Получаем запросы
        sql_queries = """
            SELECT q.*, qg.name as group_name
            FROM queries q
            LEFT JOIN query_groups qg ON q.query_group_id = qg.id
            WHERE q.project_id = %s
        """
        cursor.execute(sql_queries, (project_id,))
        queries = cursor.fetchall()

        # Получаем историю позиций
        variant_id = request.args.get("variant_id", type=int)

        subquery_params = []
        subquery_sql = "SELECT query_id, parsing_variant_id, date, MAX(id) as max_id FROM parsing_position_results"
        if variant_id:
            subquery_sql += " WHERE parsing_variant_id = %s"
            subquery_params.append(variant_id)
        subquery_sql += " GROUP BY query_id, parsing_variant_id, date"

        sql_positions = f"""
            SELECT ppr.query_id, ppr.position, ppr.date, ppr.status
            FROM parsing_position_results ppr
            INNER JOIN ({subquery_sql}) AS max_results
                ON ppr.query_id = max_results.query_id
                AND ppr.parsing_variant_id = max_results.parsing_variant_id
                AND ppr.date = max_results.date
                AND ppr.id = max_results.max_id
            JOIN queries q ON ppr.query_id = q.id
            WHERE q.project_id = %s
        """

        params = subquery_params + [project_id]
        sql_positions += " ORDER BY ppr.date"

        cursor.execute(sql_positions, tuple(params))
        all_positions = cursor.fetchall()

        # Собираем все уникальные даты
        all_dates = sorted(
            list(set(row["date"] for row in all_positions if row["date"]))
        )

        # Преобразуем даты в строки для удобства
        dates = (
            [
                d.strftime("%Y-%m-%d") if isinstance(d, type(all_dates[0])) else d
                for d in all_dates
            ]
            if all_dates
            else []
        )

        # Реструктурируем `positions`, включая статус
        positions = {}
        for row in all_positions:
            query_id = row["query_id"]
            date_obj = row["date"]
            date_str = (
                date_obj.strftime("%Y-%m-%d")
                if hasattr(date_obj, "strftime")
                else str(date_obj)
            )
            if query_id not in positions:
                positions[query_id] = {}
            positions[query_id][date_str] = {
                "position": row["position"],
                "status": row["status"],
            }

        return jsonify(
            {
                "success": True,
                "positions": positions,
                "dates": dates,
                "queries": queries,
            }
        )

    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при получении данных позиций для проекта {project_id}: {e}",
                exc_info=True,
            )
        return jsonify({"success": False, "message": "Внутренняя ошибка сервера."}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@positions_parsing_bp.route(
    "/api/projects/<int:project_id>/available-dates", methods=["GET"]
)
@login_required
def get_available_dates(project_id):
    """
    Возвращает список доступных дат для фильтрации.
    """
    variant_id = request.args.get("variant_id", type=int)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT DISTINCT ppr.date
        FROM parsing_position_results ppr
        JOIN queries q ON ppr.query_id = q.id
        JOIN projects p ON q.project_id = p.id
        WHERE q.project_id = %s AND p.user_id = %s
    """
    params = [project_id, current_user.id]

    if variant_id:
        query += " AND ppr.parsing_variant_id = %s"
        params.append(variant_id)

    query += " ORDER BY ppr.date DESC"

    cursor.execute(query, tuple(params))
    dates = [row["date"].strftime("%Y-%m-%d") for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return jsonify(dates)
