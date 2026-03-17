import logging
from flask import Blueprint, request, jsonify, render_template, Response, send_file
from flask_login import login_required, current_user
from app.db.database import get_db_connection
from app.models import Project, QueryGroup, Query, ParsingPositionResult
import csv
import io
import pandas as pd

import os
from app.db_config import LOGGING_ENABLED

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "cluster_editor_routes.log")
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


# Создание Blueprint для эндпоинтов редактора кластеров
cluster_editor_bp = Blueprint("cluster_editor_bp", __name__)


@cluster_editor_bp.route("/cluster-editor/<int:project_id>")
@login_required
def cluster_editor(project_id):
    """
    Отображает страницу редактора кластеров для указанного проекта.
    """
    if LOGGING_ENABLED:
        logger.info(
            f"Запрос на страницу редактора кластеров для проекта ID: {project_id}"
        )
    try:
        # Проверяем, что проект принадлежит текущему пользователю
        project = Project.get_by_id(project_id)
        if not project or project.user_id != current_user.id:
            if LOGGING_ENABLED:
                logger.warning(
                    f"Проект ID: {project_id} не найден или нет доступа для пользователя ID: {current_user.id}"
                )
            return "Проект не найден или у вас нет доступа.", 404
        if LOGGING_ENABLED:
            logger.info(f"Проект ID: {project_id} найден, владелец: {current_user.id}")

        # Получаем все группы и их ключевые слова для проекта
        groups = QueryGroup.get_groups_with_queries(project_id)
        if LOGGING_ENABLED:
            logger.info(f"Найдено {len(groups)} групп для проекта ID: {project_id}")

        # Получаем ключевые слова без группы
        unassigned_queries_data = Query.get_unassigned_queries(project_id)
        unassigned_queries = [
            {"id": q.id, "name": q.query_text, "volume": q.frequency or 0}
            for q in unassigned_queries_data
        ]
        if LOGGING_ENABLED:
            logger.info(
                f"Найдено {len(unassigned_queries)} некластеризованных запросов для проекта ID: {project_id}"
            )

        return render_template(
            "cluster_editor.html",
            project=project,
            groups=groups,
            unassigned_queries=unassigned_queries,
        )
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при загрузке редактора кластеров для проекта ID: {project_id}: {e}",
                exc_info=True,
            )
        return "Внутренняя ошибка сервера", 500


@cluster_editor_bp.route("/api/clusters/move-keyword", methods=["POST"])
@login_required
@login_required
def move_keyword():
    """
    Перемещает ключевое слово в другую группу.
    Принимает JSON: { "keyword_id": <id>, "target_group_id": <id> }
    """
    data = request.get_json()
    keyword_id = data.get("keyword_id")
    target_group_id = data.get("target_group_id")

    if LOGGING_ENABLED:
        logger.info(
            f"Запрос на перемещение ключевого слова ID: {keyword_id} в группу ID: {target_group_id}"
        )

    if not keyword_id or not target_group_id:
        if LOGGING_ENABLED:
            logger.warning(
                f"Неверный запрос на перемещение: keyword_id={keyword_id}, target_group_id={target_group_id}"
            )
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Необходимы 'keyword_id' и 'target_group_id'.",
                }
            ),
            400,
        )

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Обновляем query_group_id для ключевого слова
        # Если target_group_id это строка 'null', преобразуем ее в None для записи NULL в БД
        db_target_group_id = None if target_group_id == "null" else target_group_id
        cursor.execute(
            "UPDATE queries SET query_group_id = %s WHERE id = %s",
            (db_target_group_id, keyword_id),
        )
        conn.commit()

        cursor.close()
        conn.close()

        if LOGGING_ENABLED:
            logger.info(
                f"Ключевое слово ID: {keyword_id} успешно перемещено в группу ID: {target_group_id}"
            )
        return jsonify(
            {"status": "success", "message": "Ключевое слово успешно перемещено."}
        )
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при перемещении ключевого слова ID {keyword_id}: {e}",
                exc_info=True,
            )
        return jsonify({"status": "error", "message": f"Произошла ошибка: {e}"}), 500


@cluster_editor_bp.route("/api/clusters/merge", methods=["POST"])
@login_required
def merge_clusters():
    """
    Объединяет две группы кластеров.
    Принимает JSON: { "source_group_id": <id>, "target_group_id": <id> }
    """
    data = request.get_json()
    source_group_id = data.get("source_group_id")
    target_group_id = data.get("target_group_id")

    if LOGGING_ENABLED:
        logger.info(
            f"Запрос на объединение группы ID: {source_group_id} с группой ID: {target_group_id}"
        )

    if not source_group_id or not target_group_id:
        if LOGGING_ENABLED:
            logger.warning(
                "Отсутствуют 'source_group_id' или 'target_group_id' в запросе на объединение."
            )
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Необходимы 'source_group_id' и 'target_group_id'.",
                }
            ),
            400,
        )

    if source_group_id == target_group_id:
        if LOGGING_ENABLED:
            logger.warning(
                f"Попытка объединить группу саму с собой: ID {source_group_id}."
            )
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Исходная и целевая группы не могут быть одинаковыми.",
                }
            ),
            400,
        )

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Переносим все запросы из исходной группы в целевую
        cursor.execute(
            "UPDATE queries SET query_group_id = %s WHERE query_group_id = %s",
            (target_group_id, source_group_id),
        )

        # Удаляем исходную группу
        cursor.execute("DELETE FROM query_groups WHERE id = %s", (source_group_id,))

        conn.commit()

        cursor.close()
        conn.close()

        if LOGGING_ENABLED:
            logger.info(
                f"Группы {source_group_id} и {target_group_id} успешно объединены."
            )
        return jsonify({"status": "success", "message": "Группы успешно объединены."})
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при объединении групп {source_group_id} и {target_group_id}: {e}",
                exc_info=True,
            )
        return jsonify({"status": "error", "message": f"Произошла ошибка: {e}"}), 500


@cluster_editor_bp.route("/api/clusters/rename", methods=["POST"])
@login_required
def rename_cluster():
    """
    Переименовывает группу кластеров.
    Принимает JSON: { "group_id": <id>, "new_name": "<новое_имя>" }
    """
    data = request.get_json()
    group_id = data.get("group_id")
    new_name = data.get("new_name")

    if LOGGING_ENABLED:
        logger.info(f"Запрос на переименование группы ID: {group_id} в '{new_name}'")

    if not group_id or not new_name:
        if LOGGING_ENABLED:
            logger.warning(
                "Отсутствуют 'group_id' или 'new_name' в запросе на переименование."
            )
        return (
            jsonify(
                {"status": "error", "message": "Необходимы 'group_id' и 'new_name'."}
            ),
            400,
        )

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE query_groups SET name = %s WHERE id = %s", (new_name, group_id)
        )
        conn.commit()

        cursor.close()
        conn.close()

        if LOGGING_ENABLED:
            logger.info(f"Группа ID {group_id} успешно переименована в '{new_name}'.")
        return jsonify(
            {"status": "success", "message": "Группа успешно переименована."}
        )
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при переименовании группы ID {group_id}: {e}", exc_info=True
            )
        return jsonify({"status": "error", "message": f"Произошла ошибка: {e}"}), 500


@cluster_editor_bp.route("/api/clusters/delete", methods=["DELETE"])
@login_required
def delete_cluster():
    """
    Удаляет группу кластеров и освобождает связанные ключевые слова.
    Принимает JSON: { "group_id": <id> }
    """
    data = request.get_json()
    group_id = data.get("group_id")

    if LOGGING_ENABLED:
        logger.info(f"Запрос на удаление группы ID: {group_id}")

    if not group_id:
        if LOGGING_ENABLED:
            logger.warning("Отсутствует 'group_id' в запросе на удаление.")
        return jsonify({"status": "error", "message": "Необходим 'group_id'."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Устанавливаем query_group_id в NULL для всех связанных запросов
        cursor.execute(
            "UPDATE queries SET query_group_id = NULL WHERE query_group_id = %s",
            (group_id,),
        )

        # Удаляем саму группу
        cursor.execute("DELETE FROM query_groups WHERE id = %s", (group_id,))

        conn.commit()

        cursor.close()
        conn.close()

        if LOGGING_ENABLED:
            logger.info(
                f"Группа ID {group_id} успешно удалена, ключевые слова освобождены."
            )
        return jsonify(
            {
                "status": "success",
                "message": "Группа удалена, ключевые слова освобождены.",
            }
        )
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при удалении группы ID {group_id}: {e}", exc_info=True
            )
        return jsonify({"status": "error", "message": f"Произошла ошибка: {e}"}), 500


@cluster_editor_bp.route("/api/clusters/create", methods=["POST"])
@login_required
def create_cluster():
    """
    Создает новую пустую группу (кластер).
    Принимает JSON: { "name": "<имя_группы>", "project_id": <id_проекта> }
    """
    data = request.get_json()
    name = data.get("name")
    project_id = data.get("project_id")

    if LOGGING_ENABLED:
        logger.info(f"Запрос на создание группы '{name}' для проекта ID: {project_id}")

    if not name or not project_id:
        if LOGGING_ENABLED:
            logger.warning(
                "Отсутствуют 'name' или 'project_id' в запросе на создание группы."
            )
        return (
            jsonify(
                {"status": "error", "message": "Необходимы 'name' и 'project_id'."}
            ),
            400,
        )

    try:
        # Проверяем, что проект принадлежит текущему пользователю
        project = Project.get_by_id(project_id)
        if not project or project.user_id != current_user.id:
            if LOGGING_ENABLED:
                logger.warning(
                    f"Попытка создания группы в чужом проекте. Пользователь ID {current_user.id}, проект ID {project_id}"
                )
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Проект не найден или у вас нет доступа.",
                    }
                ),
                404,
            )

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO query_groups (name, project_id) VALUES (%s, %s)",
            (name, project_id),
        )
        new_group_id = cursor.lastrowid

        conn.commit()

        cursor.close()
        conn.close()

        if LOGGING_ENABLED:
            logger.info(
                f"Группа '{name}' (ID: {new_group_id}) успешно создана для проекта ID {project_id}."
            )
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Группа успешно создана.",
                    "group_id": new_group_id,
                }
            ),
            201,
        )
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при создании группы '{name}' для проекта ID {project_id}: {e}",
                exc_info=True,
            )
        return jsonify({"status": "error", "message": f"Произошла ошибка: {e}"}), 500


@cluster_editor_bp.route("/api/clusters/download/<int:project_id>", methods=["GET"])
@login_required
def download_clusters(project_id):
    """
    Выгружает кластеризованные запросы и их релевантные URL в виде CSV файла.
    """
    if LOGGING_ENABLED:
        logger.info(f"Запрос на выгрузку кластеров для проекта ID: {project_id}")

    try:
        # Проверка доступа к проекту
        project = Project.get_by_id(project_id)
        if not project or project.user_id != current_user.id:
            if LOGGING_ENABLED:
                logger.warning(
                    f"Попытка выгрузки кластеров из чужого проекта. Пользователь ID {current_user.id}, проект ID {project_id}"
                )
            return "Проект не найден или у вас нет доступа.", 404

        # Получение всех запросов проекта
        queries = Query.get_by_project_id(project_id)
        if not queries:
            return "В проекте нет запросов для выгрузки.", 404

        file_format = request.args.get("format", "csv_utf8")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        data = []
        # Получаем все группы, чтобы потом сопоставить имя группы
        groups = {g.id: g.name for g in QueryGroup.get_by_project_id(project_id)}

        for query in queries:
            cursor.execute(
                """
                SELECT url_found, top_10_urls
                FROM parsing_position_results
                WHERE query_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (query.id,),
            )
            result = cursor.fetchone()

            top_10_urls = ""
            url_found = ""
            if result:
                # Используем get(), но затем проверяем на None, чтобы гарантировать строку
                raw_top_10 = result.get("top_10_urls")
                raw_url_found = result.get("url_found")
                # Заменяем None на пустую строку
                top_10_urls = raw_top_10 if raw_top_10 is not None else ""
                url_found = raw_url_found if raw_url_found is not None else ""
                # if LOGGING_ENABLED:
                # logger.info(f"Результат для query_id {query.id}: top_10_urls='{top_10_urls}', url_found='{url_found}'")
            else:
                if LOGGING_ENABLED:
                    logger.info(
                        f"Для query_id {query.id} результаты парсинга не найдены."
                    )

            group_name = groups.get(query.query_group_id, "")

            data.append(
                {
                    "name": query.query_text,
                    "group_name": group_name,
                    "target": url_found,
                    "top_10_urls": top_10_urls,
                    "Частотность": query.frequency or 0,
                }
            )

        cursor.close()
        conn.close()

        if file_format == "xlsx":
            df = pd.DataFrame(data)

            # Преобразуем top_10_urls в отдельные колонки
            top_urls_expanded = []
            for item in data:
                top_10_str = item["top_10_urls"]
                if top_10_str and top_10_str.strip():
                    try:
                        # Предполагаем, что top_10_urls хранится как JSON строка
                        import json

                        top_10_list = json.loads(top_10_str)
                    except json.JSONDecodeError:
                        # Если не JSON, пробуем разделить по запятым
                        top_10_list = [
                            url.strip() for url in top_10_str.split(",") if url.strip()
                        ]
                else:
                    top_10_list = []

                # Добавляем до 10 URLов в отдельные колонки
                top_row = {}
                for i in range(10):
                    col_name = f"Топ-{i+1}"
                    if i < len(top_10_list):
                        top_row[col_name] = top_10_list[i]
                    else:
                        top_row[col_name] = ""
                top_urls_expanded.append(top_row)

            # Объединяем основные данные с данными Топ URLов
            expanded_data = []
            for i, item in enumerate(data):
                new_item = {**item}
                new_item.update(top_urls_expanded[i])
                # Удаляем оригинальную колонку top_10_urls, так как она теперь разделена
                del new_item["top_10_urls"]
                expanded_data.append(new_item)

            df = pd.DataFrame(expanded_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Кластеры")
            output.seek(0)

            return send_file(
                output,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=f"cluster_results_{project_id}.xlsx",
            )

        else:  # CSV-форматы
            output = io.StringIO()
            writer = csv.writer(output)
            encoding = "windows-1251" if file_format == "csv_win1251" else "utf-8"

            # Формируем заголовки для CSV с учетом разделенных топ URLов
            base_headers = ["name", "group_name", "target", "Частотность"]
            top_headers = [f"Топ-{i+1}" for i in range(10)]
            headers = base_headers + top_headers

            writer.writerow(headers)

            for item in data:
                top_10_str = item["top_10_urls"]
                if top_10_str and top_10_str.strip():
                    try:
                        import json

                        top_10_list = json.loads(top_10_str)
                    except json.JSONDecodeError:
                        top_10_list = [
                            url.strip() for url in top_10_str.split(",") if url.strip()
                        ]
                else:
                    top_10_list = []

                # Формируем строку данных
                row = [
                    item["name"],
                    item["group_name"],
                    item["target"],
                    item["Частотность"],
                ]

                # Добавляем топ URLы
                for i in range(10):
                    if i < len(top_10_list):
                        row.append(top_10_list[i])
                    else:
                        row.append("")

                if encoding == "windows-1251":
                    encoded_row = [
                        str(s).encode("windows-1251", "replace").decode("windows-1251")
                        for s in row
                    ]
                    writer.writerow(encoded_row)
                else:
                    writer.writerow(row)

            output.seek(0)

            mimetype = "text/csv"
            charset = f"; charset={encoding}"

            return Response(
                output.getvalue().encode(encoding),
                mimetype=mimetype + charset,
                headers={
                    "Content-Disposition": f"attachment;filename=cluster_results_{project_id}.csv"
                },
            )

    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при выгрузке кластеров для проекта ID {project_id}: {e}",
                exc_info=True,
            )
        return "Внутренняя ошибка сервера", 500
