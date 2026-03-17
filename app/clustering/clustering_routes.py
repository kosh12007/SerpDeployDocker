from flask import Blueprint, request, jsonify, render_template
from flask_login import current_user, login_required
from .clustering_service import HardClusterizer
from ..models import Project
import logging
import os
from app.db_config import LOGGING_ENABLED

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "clustering_routes.log")
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

# Создание блюпринта для кластеризации
clustering_bp = Blueprint("clustering_bp", __name__, url_prefix="/api/clusters")


@clustering_bp.route("/", methods=["GET"])
@login_required
def clustering_page():
    """
    Отображает страницу инструмента кластеризации.
    """
    try:
        # Получаем все проекты текущего пользователя для выпадающего списка
        user_id = current_user.id
        if LOGGING_ENABLED:
            logger.info(f"Получение проектов для пользователя ID: {user_id}")
        projects = Project.get_by_user_id(user_id)
        if LOGGING_ENABLED:
            logger.info(
                f"Найдено {len(projects)} проектов для пользователя ID: {user_id}"
            )
        return render_template("clustering.html", projects=projects)
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при загрузке страницы кластеризации: {e}", exc_info=True
            )
        return (
            jsonify(
                {
                    "error": "Внутренняя ошибка сервера при загрузке страницы кластеризации"
                }
            ),
            500,
        )


@clustering_bp.route("/preview", methods=["POST"])
@login_required
def preview_clustering():
    """
    Эндпоинт для предпросмотра результатов кластеризации.
    Принимает project_id и threshold, возвращает "было" и "стало".
    """
    data = request.json
    project_id = data.get("project_id")
    threshold = data.get("threshold")

    if not project_id or not threshold:
        return jsonify({"error": "Необходимо указать project_id и threshold"}), 400

    try:
        project_id = int(project_id)
        threshold = int(threshold)
    except (ValueError, TypeError):
        return (
            jsonify({"error": "project_id и threshold должны быть целыми числами"}),
            400,
        )

    if LOGGING_ENABLED:
        logger.info(
            f"Запрос на предпросмотр кластеризации для проекта ID: {project_id} с порогом: {threshold}"
        )

    try:
        with HardClusterizer(project_id=project_id, threshold=threshold) as clusterizer:
            # 1. Загружаем данные (ключевые слова и их SERP)
            clusterizer.load_keywords_with_serps()

            # 2. Выполняем кластеризацию для получения "стало"
            new_clusters_raw = clusterizer.run_clustering()

            # 3. Получаем текущую структуру групп ("было")
            was_data = clusterizer.get_current_groups()

            # 4. Форматируем "стало" для ответа
            became_data = []
            for cluster in new_clusters_raw:
                became_data.append(
                    {
                        "name": cluster["main_keyword"]["name"],
                        "total_volume": sum(
                            member["volume"] for member in cluster["members"]
                        ),
                        "keywords": [member["name"] for member in cluster["members"]],
                    }
                )

            # 5. Получаем некластеризованные запросы
            clustered_keyword_ids = {
                member["id"]
                for cluster in new_clusters_raw
                for member in cluster["members"]
            }
            all_keyword_ids = {kw["id"] for kw in clusterizer.keywords_data}
            unclustered_ids = all_keyword_ids - clustered_keyword_ids

            unclustered_keywords = [
                kw for kw in clusterizer.keywords_data if kw["id"] in unclustered_ids
            ]
            if unclustered_keywords:
                became_data.append(
                    {
                        "name": "Некластеризованные запросы",
                        "total_volume": sum(
                            kw["volume"] for kw in unclustered_keywords
                        ),
                        "keywords": [kw["name"] for kw in unclustered_keywords],
                    }
                )

        return jsonify({"was": was_data, "became": became_data})

    except ValueError as e:
        if LOGGING_ENABLED:
            logger.warning(f"Ошибка валидации в preview_clustering: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Непредвиденная ошибка в preview_clustering: {e}", exc_info=True
            )
        return jsonify({"error": "Внутренняя ошибка сервера при кластеризации"}), 500


@clustering_bp.route("/apply", methods=["POST"])
@login_required
def apply_clustering():
    """
    Эндпоинт для применения новой структуры кластеризации.
    """
    data = request.json
    project_id = data.get("project_id")
    threshold = data.get("threshold")

    if not project_id or not threshold:
        return jsonify({"error": "Необходимо указать project_id и threshold"}), 400

    try:
        project_id = int(project_id)
        threshold = int(threshold)
    except (ValueError, TypeError):
        return (
            jsonify({"error": "project_id и threshold должны быть целыми числами"}),
            400,
        )

    if LOGGING_ENABLED:
        logger.info(
            f"Запрос на применение кластеризации для проекта ID: {project_id} с порогом: {threshold}"
        )

    try:
        with HardClusterizer(project_id=project_id, threshold=threshold) as clusterizer:
            # Повторяем шаги для получения новой структуры
            clusterizer.load_keywords_with_serps()
            new_clusters = clusterizer.run_clustering()

            # Применяем изменения в базе данных
            clusterizer.apply_new_clustering(new_clusters)

        return jsonify({"message": "Кластеризация успешно применена."}), 200

    except ValueError as e:
        if LOGGING_ENABLED:
            logger.warning(f"Ошибка валидации в apply_clustering: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Непредвиденная ошибка в apply_clustering: {e}", exc_info=True
            )
        return (
            jsonify(
                {"error": "Внутренняя ошибка сервера при применении кластеризации"}
            ),
            500,
        )
