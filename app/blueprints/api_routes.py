"""
API routes blueprint for SERP bot application.

Contains API endpoints for:
- Location data
- Yandex regions
- Balance checking
- Limits estimation
"""

import threading
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import os
import logging
import json
import xmltodict
import re
from time import sleep
from urllib.parse import urlparse, parse_qs
import requests
from ..db.database import get_locations, get_yandex_regions, create_connection
from ..parsing_utils import analyze_results

# from app import db # Удалено в рамках рефакторинга SQLAlchemy
from datetime import datetime
from app.db_config import LOGGING_ENABLED

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "api_routes.log")
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
if LOGGING_ENABLED:
    logger.info(f"Логгер для {__name__} настроен.")
# --- Конец настройки логгера ---

api_routes = Blueprint("api", __name__)


@api_routes.route("/locations")
@login_required
def api_locations():
    """Возвращает список локаций с пагинацией и поиском."""
    search_query = request.args.get("search", "")
    page = request.args.get("page", 1, type=int)

    result = get_locations(search_query=search_query, page=page)

    # Форматируем для Select2
    formatted_results = {
        "results": [
            {"id": loc["criteria_id"], "text": loc["canonical_name"]}
            for loc in result["locations"]
        ],
        "pagination": {"more": (page * 30) < result["total_count"]},
    }
    return jsonify(formatted_results)


@api_routes.route("/yandex-regions")
@login_required
def api_yandex_regions():
    """Возвращает список регионов Яндекса с пагинацией и поиском."""
    search_query = request.args.get("search", "")
    page = request.args.get("page", 1, type=int)

    result = get_yandex_regions(search_query=search_query, page=page)

    formatted_results = {
        "results": [
            {"id": region["region_id"], "text": region["region_name"]}
            for region in result["regions"]
        ],
        "pagination": {"more": (page * 30) < result["total_count"]},
    }
    return jsonify(formatted_results)


@api_routes.route("/devices")
@login_required
def api_devices():
    """Возвращает список устройств."""
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, name FROM devices")
        devices = cursor.fetchall()

        # Форматируем для Select2
        formatted_results = {
            "results": [{"id": dev["id"], "text": dev["name"]} for dev in devices],
            "pagination": {"more": False},
        }
        return jsonify(formatted_results)
    except Exception as e:
        logger.error(f"Ошибка получения списка устройств: {e}", exc_info=True)
        return jsonify({"error": "Ошибка получения списка устройств"}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


@api_routes.route("/check-balance")
@login_required
def api_check_balance():
    """Проверяет баланс через API xmlriver.com"""
    try:
        api_url = os.getenv("API_KEY")
        if not api_url:
            raise ValueError("API_KEY не найден в .env")

        parsed_url = urlparse(api_url)
        query_params = parse_qs(parsed_url.query)
        user = query_params.get("user", [None])[0]
        key = query_params.get("key", [None])[0]

        if not user or not key:
            raise ValueError("Не удалось извлечь user или key из API_KEY")
        logger.info(f"Запуск роута получение баланса.")
        balance_url = "https://xmlriver.com/api/get_balance/"
        params = {"user": user, "key": key}

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


@api_routes.route("/estimate-limits", methods=["POST"])
@login_required
def api_estimate_limits():
    """
    Оценивает и возвращает необходимое количество лимитов для задачи парсинга.
    """
    try:
        logger.debug(f"Запрос на оценку лимитов. Request form: {request.form}")
        # Данные приходят как form-data, а не JSON. Используем request.form.
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


@api_routes.route("/estimate-limits-parser", methods=["POST"])
@login_required
def api_estimate_limits_parser():
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


# --- CRUD операции для модели Project ---


@api_routes.route("/projects", methods=["GET"])
@login_required
def get_projects():
    """Получение списка всех проектов пользователя."""
    connection = None
    cursor = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        sql = "SELECT * FROM projects WHERE user_id = %s"
        cursor.execute(sql, (current_user.id,))
        projects = cursor.fetchall()

        # Конвертируем datetime в строку, если необходимо
        for project in projects:
            if project.get("created_at"):
                project["created_at"] = project["created_at"].isoformat()
            if project.get("updated_at"):
                project["updated_at"] = project["updated_at"].isoformat()

        return jsonify(projects)
    except Exception as e:
        logger.error(f"Ошибка получения списка проектов: {e}", exc_info=True)
        return jsonify({"error": "Ошибка получения списка проектов"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@api_routes.route("/projects", methods=["POST"])
@login_required
def create_project():
    """Создание нового проекта."""
    connection = None
    cursor = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Данные не предоставлены"}), 400

        name = data.get("name")
        url = data.get("url")
        user_id = current_user.id

        if not name or not url:
            return jsonify({"error": "Необходимо указать имя и URL проекта"}), 400

        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        sql = "INSERT INTO projects (name, url, user_id) VALUES (%s, %s, %s)"
        cursor.execute(sql, (name, url, user_id))
        connection.commit()

        # Получаем созданный проект, чтобы вернуть его в ответе
        new_project_id = cursor.lastrowid
        cursor.execute("SELECT * FROM projects WHERE id = %s", (new_project_id,))
        new_project = cursor.fetchone()

        if new_project:
            if new_project.get("created_at"):
                new_project["created_at"] = new_project["created_at"].isoformat()
            if new_project.get("updated_at"):
                new_project["updated_at"] = new_project["updated_at"].isoformat()
            return jsonify(new_project), 201
        else:
            return jsonify({"error": "Ошибка создания проекта"}), 500

    except Exception as e:
        logger.error(f"Ошибка создания проекта: {e}", exc_info=True)
        return jsonify({"error": "Внутренняя ошибка сервера при создании проекта"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@api_routes.route("/projects/<int:project_id>", methods=["GET"])
@login_required
def get_project(project_id):
    """Получение одного проекта по ID."""
    connection = None
    cursor = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        sql = "SELECT * FROM projects WHERE id = %s"
        cursor.execute(sql, (project_id,))
        project = cursor.fetchone()

        if not project:
            return jsonify({"error": "Проект не найден"}), 404

        # Проверяем, принадлежит ли проект текущему пользователю
        if project.get("user_id") != current_user.id:
            return jsonify({"error": "Доступ запрещен"}), 403

        if project.get("created_at"):
            project["created_at"] = project["created_at"].isoformat()
        if project.get("updated_at"):
            project["updated_at"] = project["updated_at"].isoformat()

        return jsonify(project)
    except Exception as e:
        logger.error(f"Ошибка получения проекта {project_id}: {e}", exc_info=True)
        return (
            jsonify({"error": "Внутренняя ошибка сервера при получении проекта"}),
            500,
        )
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@api_routes.route("/projects/<int:project_id>", methods=["PUT"])
@login_required
def update_project(project_id):
    """Обновление проекта по ID."""
    connection = None
    cursor = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # Сначала проверяем существование проекта и права доступа
        cursor.execute("SELECT user_id FROM projects WHERE id = %s", (project_id,))
        project_owner = cursor.fetchone()
        if not project_owner:
            return jsonify({"error": "Проект не найден"}), 404
        if project_owner["user_id"] != current_user.id:
            return jsonify({"error": "Доступ запрещен"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "Данные не предоставлены"}), 400

        name = data.get("name")
        url = data.get("url")

        if not name or not url:
            return jsonify({"error": "Необходимо указать имя и URL"}), 400

        sql = "UPDATE projects SET name = %s, url = %s WHERE id = %s"
        cursor.execute(sql, (name, url, project_id))
        connection.commit()

        # Получаем обновленный проект
        cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        updated_project = cursor.fetchone()

        if updated_project.get("created_at"):
            updated_project["created_at"] = updated_project["created_at"].isoformat()
        if updated_project.get("updated_at"):
            updated_project["updated_at"] = updated_project["updated_at"].isoformat()

        return jsonify(updated_project)

    except Exception as e:
        logger.error(f"Ошибка обновления проекта {project_id}: {e}", exc_info=True)
        return (
            jsonify({"error": "Внутренняя ошибка сервера при обновлении проекта"}),
            500,
        )
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@api_routes.route("/projects/<int:project_id>", methods=["DELETE"])
@login_required
def delete_project(project_id):
    """Удаление проекта по ID."""
    connection = None
    cursor = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # Сначала проверяем существование проекта и права доступа
        cursor.execute("SELECT user_id FROM projects WHERE id = %s", (project_id,))
        project_owner = cursor.fetchone()
        if not project_owner:
            return jsonify({"error": "Проект не найден"}), 404
        if project_owner["user_id"] != current_user.id:
            return jsonify({"error": "Доступ запрещен"}), 403

        sql = "DELETE FROM projects WHERE id = %s"
        cursor.execute(sql, (project_id,))
        connection.commit()

        if cursor.rowcount > 0:
            return jsonify({"message": "Проект успешно удален"}), 200
        else:
            # Эта ветка маловероятна, если первая проверка прошла, но для полноты
            return (
                jsonify({"error": "Ошибка удаления проекта или проект не найден"}),
                500,
            )

    except Exception as e:
        logger.error(f"Ошибка удаления проекта {project_id}: {e}", exc_info=True)
        return jsonify({"error": "Внутренняя ошибка сервера при удалении проекта"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# --- CRUD операции для модели ParsingVariant (варианты парсинга) ---


@api_routes.route("/projects/<int:project_id>/variants", methods=["GET"])
@login_required
def get_parsing_variants(project_id):
    """
    Получение списка всех вариантов парсинга для конкретного проекта.
    """
    connection = None
    cursor = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # Сначала проверяем существование проекта и права доступа
        cursor.execute("SELECT user_id FROM projects WHERE id = %s", (project_id,))
        project_owner = cursor.fetchone()
        if not project_owner:
            return jsonify({"error": "Проект не найден"}), 404
        if project_owner["user_id"] != current_user.id:
            return jsonify({"error": "Доступ запрещен"}), 403

        # Получаем варианты с названиями связанных сущностей
        sql = """
            SELECT
                pv.id, pv.project_id, pv.name, pv.search_engine_id, pv.search_type_id,
                pv.yandex_region_id, pv.location_id, pv.device_id, pv.is_active, pv.created_at,
                se.name as search_engine,
                st.name as search_type,
                yr.region_name as region,
                d.name as device,
                l.canonical_name as location
            FROM parsing_variants pv
            LEFT JOIN search_engines se ON pv.search_engine_id = se.id
            LEFT JOIN search_types st ON pv.search_type_id = st.id
            LEFT JOIN yandex_regions yr ON pv.yandex_region_id = yr.region_id
            LEFT JOIN devices d ON pv.device_id = d.id
            LEFT JOIN locations l ON pv.location_id = l.criteria_id
            WHERE pv.project_id = %s
        """
        cursor.execute(sql, (project_id,))
        variants = cursor.fetchall()

        # Форматируем результат для отображения
        formatted_variants = []
        for variant in variants:
            # Формируем подробное описание варианта
            details = [
                variant.get("search_engine"),
                variant.get("search_type"),
                variant.get("region") or variant.get("location"),
                variant.get("device"),
            ]
            # Убираем None значения и объединяем в строку
            details_str = " / ".join(filter(None, details))

            formatted_variants.append(
                {
                    "id": variant["id"],
                    "name": variant["name"],
                    "details": details_str,
                    "full_text": f"{variant['name']} ({details_str})",
                }
            )

        return jsonify(formatted_variants)

    except Exception as e:
        logger.error(
            f"Ошибка получения списка вариантов для проекта {project_id}: {e}",
            exc_info=True,
        )
        return jsonify({"error": "Ошибка получения списка вариантов"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# --- CRUD операции для модели Query (запросы) ---


@api_routes.route("/projects/<int:project_id>/queries", methods=["GET"])
@login_required
def get_queries(project_id):
    """Получение списка всех запросов для конкретного проекта с использованием SQL."""
    connection = None
    cursor = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # Проверка, что проект существует и принадлежит пользователю
        cursor.execute("SELECT user_id FROM projects WHERE id = %s", (project_id,))
        project_owner = cursor.fetchone()
        if not project_owner:
            return jsonify({"error": "Проект не найден"}), 404
        if project_owner["user_id"] != current_user.id:
            return jsonify({"error": "Доступ запрещен"}), 403

        # SQL-запрос для получения запросов с именем группы
        sql = """
            SELECT q.*, qg.name as group_name
            FROM queries q
            LEFT JOIN query_groups qg ON q.query_group_id = qg.id
            WHERE q.project_id = %s
        """
        cursor.execute(sql, (project_id,))
        queries = cursor.fetchall()

        # Конвертация datetime в строку
        for query in queries:
            if query.get("created_at"):
                query["created_at"] = query["created_at"].isoformat()
            if query.get("updated_at"):
                query["updated_at"] = query["updated_at"].isoformat()

        return jsonify(queries)

    except Exception as e:
        logger.error(
            f"Ошибка получения запросов для проекта {project_id}: {e}", exc_info=True
        )
        return (
            jsonify({"error": "Внутренняя ошибка сервера при получении запросов"}),
            500,
        )
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@api_routes.route("/projects/<int:project_id>/queries", methods=["POST"])
@login_required
def add_queries(project_id):
    """
    Добавление новых запросов в проект с использованием "сырых" SQL-запросов.
    Тело запроса: {"queries": [{"text": "купить слона", "group": "продажи"}, ...]}
    """
    connection = None
    cursor = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # 1. Проверка существования проекта и прав доступа
        cursor.execute("SELECT user_id FROM projects WHERE id = %s", (project_id,))
        project_owner = cursor.fetchone()
        if not project_owner:
            return jsonify({"error": "Проект не найден"}), 404
        if project_owner["user_id"] != current_user.id:
            return jsonify({"error": "Доступ запрещен"}), 403

        # 2. Получение и валидация данных
        data = request.get_json()
        if not data or "queries" not in data:
            return (
                jsonify(
                    {"error": "Неверный формат данных. Ожидается {'queries': [...]}"}
                ),
                400,
            )
        queries_to_add = data["queries"]
        if not isinstance(queries_to_add, list):
            return jsonify({"error": "'queries' должен быть списком."}), 400

        created_queries_ids = []

        # 3. Основной цикл обработки запросов в транзакции
        for q in queries_to_add:
            query_text = q.get("text")
            group_name = q.get("group")

            if not query_text:
                continue

            group_id = None
            if group_name:
                # Ищем существующую группу
                cursor.execute(
                    "SELECT id FROM query_groups WHERE name = %s AND project_id = %s",
                    (group_name, project_id),
                )
                group = cursor.fetchone()
                if group:
                    group_id = group["id"]
                else:
                    # Создаем новую группу, если не найдена
                    cursor.execute(
                        "INSERT INTO query_groups (name, project_id) VALUES (%s, %s)",
                        (group_name, project_id),
                    )
                    group_id = cursor.lastrowid

            # Добавляем сам запрос
            cursor.execute(
                "INSERT INTO queries (project_id, query_text, query_group_id) VALUES (%s, %s, %s)",
                (project_id, query_text, group_id),
            )
            created_queries_ids.append(cursor.lastrowid)

        # Коммитим транзакцию только после успешной обработки всех запросов
        connection.commit()

        return (
            jsonify(
                {
                    "message": "Запросы успешно добавлены",
                    "created_query_ids": created_queries_ids,
                }
            ),
            201,
        )

    except Exception as e:
        if connection:
            connection.rollback()
        logger.error(
            f"Ошибка добавления запросов в проект {project_id}: {e}", exc_info=True
        )
        return (
            jsonify({"error": "Внутренняя ошибка сервера при добавлении запросов"}),
            500,
        )
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@api_routes.route("/projects/<int:project_id>/queries/upload", methods=["POST"])
@login_required
def upload_queries_csv(project_id):
    """Заглушка для загрузки запросов из CSV."""
    # Проверка на существование проекта и права доступа
    project = Project.get_by_id(project_id)
    if not project:
        return jsonify({"error": "Проект не найден"}), 404
    if project.user_id != current_user.id:
        return jsonify({"error": "Доступ запрещен"}), 403

    return jsonify({"message": "CSV upload will be implemented later"}), 501


@api_routes.route("/queries/<int:query_id>", methods=["DELETE"])
@login_required
def delete_query(query_id):
    """Удаление запроса по его ID с использованием SQL."""
    connection = None
    cursor = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # 1. Получаем project_id из запроса, чтобы проверить права
        cursor.execute("SELECT project_id FROM queries WHERE id = %s", (query_id,))
        query_info = cursor.fetchone()
        if not query_info:
            return jsonify({"error": "Запрос не найден"}), 404

        # 2. Проверяем права на проект
        project_id = query_info["project_id"]
        cursor.execute("SELECT user_id FROM projects WHERE id = %s", (project_id,))
        project_owner = cursor.fetchone()
        if not project_owner or project_owner["user_id"] != current_user.id:
            return jsonify({"error": "Доступ запрещен"}), 403

        # 3. Удаляем запрос
        cursor.execute("DELETE FROM queries WHERE id = %s", (query_id,))
        connection.commit()

        if cursor.rowcount > 0:
            return jsonify({"message": "Запрос успешно удален"}), 200
        else:
            return jsonify({"error": "Ошибка удаления запроса"}), 500

    except Exception as e:
        if connection:
            connection.rollback()
        logger.error(f"Ошибка удаления запроса {query_id}: {e}", exc_info=True)
        return jsonify({"error": "Внутренняя ошибка сервера при удалении запроса"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


from ..positions_parsing.core.parser import search_xmlriver


def _run_parsing_task(app, project_id, variant_ids, date_str, user_id):
    """
    Выполняет парсинг позиций в фоновом потоке, используя прямые SQL-запросы.
    """
    with app.app_context():
        connection = None
        cursor = None
        try:
            logger.info(
                f"Начало фоновой задачи для проекта {project_id} с вариантами {variant_ids}"
            )
            parsing_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            connection = create_connection()
            cursor = connection.cursor(dictionary=True)

            # 1. Получение проекта и проверка прав
            cursor.execute(
                "SELECT * FROM projects WHERE id = %s AND user_id = %s",
                (project_id, user_id),
            )
            project = cursor.fetchone()
            if not project:
                logger.error(
                    f"Проект с ID {project_id} не найден или доступ запрещен в фоновой задаче."
                )
                return

            # 2. Получение вариантов парсинга
            if not variant_ids:
                logger.error(
                    f"Список ID вариантов парсинга пуст для проекта {project_id}."
                )
                return
            placeholders = ", ".join(["%s"] * len(variant_ids))
            sql_variants = f"""
                SELECT
                    pv.*,
                    se.name as search_engine_name,
                    st.api_parameter as search_type_name,
                    # st.name as search_type_name,
                    yr.region_name,
                    d.api_parameter as device_api_name,
                    l.canonical_name as location_name
                FROM parsing_variants pv
                LEFT JOIN search_engines se ON pv.search_engine_id = se.id
                LEFT JOIN search_types st ON pv.search_type_id = st.id
                LEFT JOIN yandex_regions yr ON pv.yandex_region_id = yr.region_id
                LEFT JOIN devices d ON pv.device_id = d.id
                LEFT JOIN locations l ON pv.location_id = l.criteria_id
                WHERE pv.id IN ({placeholders})
            """
            cursor.execute(sql_variants, tuple(variant_ids))
            variants = cursor.fetchall()
            logger.info(f"Найдено {len(variants)} вариантов парсинга.")
            if not variants:
                logger.error(f"Варианты парсинга с ID {variant_ids} не найдены.")
                return

            # 3. Получение запросов
            cursor.execute("SELECT * FROM queries WHERE project_id = %s", (project_id,))
            queries = cursor.fetchall()
            logger.info(f"Найдено {len(queries)} запросов для парсинга.")
            if not queries:
                logger.warning(f"Для проекта {project_id} не найдено запросов.")
                return

            # 4. Настройка клиента XmlRiver
            # 4. Основной цикл парсинга
            for variant in variants:
                # Определяем BASE_URL в зависимости от поисковой системы
                search_engine_name = variant.get("search_engine_name", "").lower()
                search_type_name = variant.get("search_type_name", "").lower()

                logger.info(
                    f"Проверка варианта: SE_name='{search_engine_name}', Type_name='{search_type_name}'"
                )

                if search_engine_name == "google":
                    BASE_URL = "http://xmlriver.com/search/xml"
                elif search_engine_name in ["yandex", "яндекс"]:
                    if search_type_name == "live":
                        logger.info(
                            f"Проверка варианта 1: SE_name='{search_engine_name}', Type_name='{search_type_name}'"
                        )
                        BASE_URL = "http://xmlriver.com/search_yandex/xml"
                    else:
                        logger.info(
                            f"Проверка варианта 2: SE_name='{search_engine_name}', Type_name='{search_type_name}'"
                        )  # search_api
                        BASE_URL = "http://xmlriver.com/yandex/xml"
                else:
                    logger.error(f"Неизвестная поисковая система: {search_engine_name}")
                    continue

                for query in queries:
                    search_params = {"query": query["query_text"]}
                    if search_engine_name in ["yandex", "яндекс"]:
                        search_params.update(
                            {
                                "lr": variant.get("yandex_region_id"),
                                "lang": "ru",
                                "domain": "ru",
                                "device": variant.get("device_api_name", "desktop"),
                                "groupby": (
                                    10 if search_type_name == "live_search" else 100
                                ),
                            }
                        )
                    else:  # google
                        search_params.update(
                            {
                                "loc": variant["location_id"],
                                "country": 2008,  # RU
                                "lr": "RU",
                                "domain": 10,  # Google .com
                                "device": (
                                    variant["device_api_name"]
                                    if variant.get("device_api_name")
                                    else "desktop"
                                ),
                                "groupby": 10,
                            }
                        )

                    api_key_url = os.getenv("API_KEY")
                    parsed_url = urlparse(api_key_url)
                    query_params_api = parse_qs(parsed_url.query)
                    user = query_params_api.get("user", [None])[0]
                    api_key = query_params_api.get("key", [None])[0]

                    search_params.update({"user": user, "key": api_key})

                    logger.info(f"Параметры для XmlRiver: {search_params}")

                    position, found_url, success, top_10_urls = search_xmlriver(
                        query=query["query_text"],
                        user=user,
                        key=api_key,
                        base_url=BASE_URL,
                        engine=variant.get("search_engine_name", "").lower(),
                        params=search_params,
                        site_url=project["url"],
                    )

                    if success:
                        logger.info(
                            f"Получены результаты от XmlRiver для запроса '{query['query_text']}'."
                        )

                        top_10_urls_json = json.dumps(top_10_urls)

                        # Используем тот же курсор для вставки
                        insert_sql = """
                            INSERT INTO parsing_position_results
                            (query_id, parsing_variant_id, position, url_found, top_10_urls, date)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        insert_params = (
                            query["id"],
                            variant["id"],
                            position,
                            found_url,
                            top_10_urls_json,
                            parsing_date,
                        )
                        cursor.execute(insert_sql, insert_params)

                    else:
                        logger.warning(
                            f"Нет результатов от XmlRiver для запроса '{query['query_text']}' и варианта '{variant['name']}'."
                        )

            connection.commit()  # Один коммит в конце
            logger.info(f"Фоновый парсинг для проекта {project_id} успешно завершен.")

        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(
                f"Ошибка в фоновой задаче парсинга для проекта {project_id}: {e}",
                exc_info=True,
            )
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()


@api_routes.route("/projects/<int:project_id>/results", methods=["GET"])
@login_required
def get_parsing_results(project_id):
    """
    Получение и фильтрация результатов парсинга для проекта.
    Фильтры (query params):
    - date_from (YYYY-MM-DD)
    - date_to (YYYY-MM-DD)
    - variants (id через запятую)
    - queries (id через запятую)
    """
    try:
        # 1. Проверка существования проекта и прав доступа
        project = Project.get_by_id(project_id)
        if not project:
            return jsonify({"error": "Проект не найден"}), 404
        if project.user_id != current_user.id:
            return jsonify({"error": "Доступ запрещен"}), 403

        # 2. Получение параметров фильтрации
        date_from_str = request.args.get("date_from")
        date_to_str = request.args.get("date_to")
        variants_str = request.args.get("variants")
        queries_str = request.args.get("queries")

        # 3. Построение динамического SQL-запроса
        params = [project_id]

        # Базовый запрос с JOIN'ами
        sql_query = """
            SELECT 
                r.id, r.position, r.url_found, r.date as parsing_date,
                q.id as query_id, q.query_text,
                v.id as variant_id, v.name as variant_name
            FROM parsing_position_results r
            JOIN queries q ON r.query_id = q.id
            JOIN parsing_variants v ON r.variant_id = v.id
            WHERE q.project_id = %s
        """

        # 4. Динамическое добавление фильтров
        if date_from_str:
            sql_query += " AND r.parsing_date &gt;= %s"
            params.append(date_from_str)

        if date_to_str:
            sql_query += " AND r.parsing_date &lt;= %s"
            params.append(date_to_str)

        if variants_str:
            try:
                variant_ids = [
                    int(vid) for vid in variants_str.split(",") if vid.strip()
                ]
                if variant_ids:
                    # Создаем плейсхолдеры для каждого ID
                    placeholders = ", ".join(["%s"] * len(variant_ids))
                    sql_query += f" AND r.variant_id IN ({placeholders})"
                    params.extend(variant_ids)
            except ValueError:
                return jsonify({"error": "Неверный формат ID вариантов"}), 400

        if queries_str:
            try:
                query_ids = [int(qid) for qid in queries_str.split(",") if qid.strip()]
                if query_ids:
                    placeholders = ", ".join(["%s"] * len(query_ids))
                    sql_query += f" AND r.query_id IN ({placeholders})"
                    params.extend(query_ids)
            except ValueError:
                return jsonify({"error": "Неверный формат ID запросов"}), 400

        sql_query += " ORDER BY r.date DESC, q.query_text;"

        # 5. Выполнение запроса
        from ..db.database import create_connection
        from mysql.connector import Error

        results = []
        connection = create_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute(sql_query, tuple(params))
                raw_results = cursor.fetchall()

                # 6. Сериализация результатов
                for row in raw_results:
                    results.append(
                        {
                            "id": row["id"],
                            "position": row["position"],
                            "url_found": row["url_found"],
                            "parsing_date": (
                                row["parsing_date"].isoformat()
                                if row["parsing_date"]
                                else None
                            ),
                            "query_id": row["query_id"],
                            "query_text": row["query_text"],
                            "variant_id": row["variant_id"],
                            "variant_name": row["variant_name"],
                        }
                    )
            except Error as e:
                logger.error(
                    f"Ошибка выполнения SQL-запроса для получения результатов: {e}",
                    exc_info=True,
                )
                return jsonify({"error": "Ошибка при получении данных из базы"}), 500
            finally:
                if "cursor" in locals() and cursor:
                    cursor.close()
                connection.close()

        return jsonify(results)

    except Exception as e:
        logger.error(
            f"Ошибка в эндпоинте get_parsing_results для проекта {project_id}: {e}",
            exc_info=True,
        )
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500
