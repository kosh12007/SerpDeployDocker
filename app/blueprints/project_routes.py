import os
import logging
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
from app.models import ParsingVariant

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "project_routes.log")
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

# Создание Blueprint для проектов
project_bp = Blueprint("project_routes", __name__, template_folder="templates")


@project_bp.route("/projects/create", methods=["GET", "POST"])
@login_required
def create_project():
    """
    Обрабатывает создание нового проекта с использованием прямого SQL-запроса.
    """
    if request.method == "POST":
        name = request.form.get("name")
        url = request.form.get("url")

        if not name or not url:
            return render_template(
                "projects/create_project.html", error="Название и URL обязательны."
            )

        # Проверяем, что пользователь авторизован
        if not current_user.is_authenticated:
            logger.error("Попытка создания проекта неавторизованным пользователем")
            return redirect(url_for("auth.login"))

        user_id = current_user.id
        logger.info(
            f"Текущий пользователь: id={user_id}, username={current_user.username}, is_authenticated={current_user.is_authenticated}"
        )

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            sql = "INSERT INTO projects (name, url, user_id) VALUES (%s, %s, %s)"
            params = (name, url, user_id)

            logger.info(
                f"Создание проекта: name={name}, url={url}, user_id={user_id}, current_user.id={current_user.id}"
            )
            logger.info(f"SQL: {sql}, params: {params}")

            cursor.execute(sql, params)
            project_id = cursor.lastrowid
            logger.info(f"Создан проект с ID: {project_id}")
            conn.commit()

            # Проверяем, что записалось в БД
            cursor.execute(
                "SELECT id, name, url, user_id FROM projects WHERE id = %s",
                (project_id,),
            )
            saved_project = cursor.fetchone()
            if saved_project:
                logger.info(
                    f"Проект после сохранения в БД: id={saved_project[0]}, name={saved_project[1]}, url={saved_project[2]}, user_id={saved_project[3]}"
                )
            else:
                logger.error(f"Проект с ID {project_id} не найден после сохранения!")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

        return redirect(url_for("project_routes.project_list"))

    return render_template("projects/create_project.html")


@project_bp.route("/projects")
@login_required
def project_list():
    """
    Отображает страницу со списком проектов текущего пользователя.
    """
    if not current_user.is_authenticated:
        logger.error("Попытка просмотра проектов неавторизованным пользователем")
        return redirect(url_for("auth.login"))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM projects WHERE user_id = %s ORDER BY created_at DESC",
            (current_user.id,),
        )
        projects = cursor.fetchall()
        logger.info(
            f"Найдено проектов для пользователя {current_user.id}: {len(projects)}"
        )
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    return render_template("projects/project_list.html", projects=projects)


@project_bp.route("/api/projects")
@login_required
def api_projects():
    """
    Возвращает JSON список проектов текущего пользователя.
    Используется для селектора проектов в хедере.
    """
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Требуется авторизация"}), 401

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Получаем только необходимые поля для селектора
        cursor.execute(
            "SELECT id, name, url FROM projects WHERE user_id = %s ORDER BY name ASC",
            (current_user.id,),
        )
        projects = cursor.fetchall()
        if LOGGING_ENABLED:
            logger.info(
                f"API: Найдено проектов для пользователя {current_user.id}: {len(projects)}"
            )
        return jsonify({"success": True, "projects": projects})
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(f"Ошибка при получении списка проектов: {e}")
        return jsonify({"success": False, "message": "Ошибка сервера"}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@project_bp.route("/projects/<int:project_id>")
@login_required
def project_detail(project_id):
    """
    Отображает детальную информацию о проекте, используя прямые SQL-запросы.
    Проверяет, что проект принадлежит текущему пользователю.
    """
    if not current_user.is_authenticated:
        logger.error("Попытка просмотра проекта неавторизованным пользователем")
        return redirect(url_for("auth.login"))

    if LOGGING_ENABLED:
        logger.debug(
            f"Загрузка данных для проекта ID: {project_id}, пользователь: {current_user.id}"
        )
    conn = None
    project = None
    variants = []
    queries = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Получаем данные проекта и проверяем принадлежность пользователю
        cursor.execute(
            "SELECT * FROM projects WHERE id = %s AND user_id = %s",
            (project_id, current_user.id),
        )
        project = cursor.fetchone()
        if LOGGING_ENABLED:
            logger.debug(f"Найден проект: {project}")

        if not project:
            logger.warning(
                f"Проект {project_id} не найден или не принадлежит пользователю {current_user.id}"
            )
            flash("Проект не найден или у вас нет доступа к нему", "error")
            abort(404)

        # 2. Получаем варианты парсинга с названиями связанных сущностей
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
            variant.name = variant.name
            variants.append(variant)

        if LOGGING_ENABLED:
            logger.debug(f"Найдены и отформатированы варианты: {variants}")

        # 3. Получаем запросы с названиями групп
        sql_queries = """
            SELECT q.*, qg.name as group_name
            FROM queries q
            LEFT JOIN query_groups qg ON q.query_group_id = qg.id
            WHERE q.project_id = %s
        """
        cursor.execute(sql_queries, (project_id,))
        queries = cursor.fetchall()
        if LOGGING_ENABLED:
            logger.debug(f"Найдены запросы: {queries}")

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    return render_template(
        "projects/project_detail.html",
        project=project,
        variants=variants,
        queries=queries,
    )


@project_bp.route("/projects/<int:project_id>/variants", methods=["POST"])
@login_required
def add_parsing_variant(project_id):
    """
    Добавляет новый вариант парсинга для проекта.
    Проверяет, что проект принадлежит текущему пользователю.
    """
    if not current_user.is_authenticated:
        logger.error("Попытка добавления варианта неавторизованным пользователем")
        if request.is_json:
            return {"success": False, "message": "Требуется авторизация"}, 401
        return redirect(url_for("auth.login"))

    # Проверяем принадлежность проекта пользователю
    conn_check = None
    try:
        conn_check = get_db_connection()
        cursor_check = conn_check.cursor(dictionary=True)
        cursor_check.execute(
            "SELECT id, user_id FROM projects WHERE id = %s", (project_id,)
        )
        project_check = cursor_check.fetchone()

        if not project_check:
            logger.warning(f"Проект {project_id} не найден")
            if request.is_json:
                return {"success": False, "message": "Проект не найден"}, 404
            flash("Проект не найден", "error")
            return redirect(url_for("project_routes.project_list"))

        if project_check["user_id"] != current_user.id:
            logger.warning(
                f"Попытка добавления варианта к проекту {project_id} пользователем {current_user.id}, владелец: {project_check['user_id']}"
            )
            if request.is_json:
                return {"success": False, "message": "Доступ запрещен"}, 403
            flash("Доступ запрещен", "error")
            return redirect(url_for("project_routes.project_list"))
    finally:
        if conn_check and conn_check.is_connected():
            cursor_check.close()
            conn_check.close()

    # Проверяем, является ли запрос JSON-запросом
    if request.is_json:
        data = request.get_json()
        logger.info(f"Received JSON data for device: {data}")
        project_id = data.get("project_id", project_id)
        name = data.get("name")
        search_engine_id = data.get("search_engine_id")
        search_type_id = data.get("search_type_id")
        yandex_region_id = (
            data.get("yandex_region_id")
            if data.get("yandex_region_id") not in [None, ""]
            else None
        )
        location_id = (
            data.get("location_id")
            if data.get("location_id") not in [None, ""]
            else None
        )
        device_id = data.get("device_id")
        logger.info(f"Final device_id to be saved: {device_id}")
        page_limit = data.get("page_limit") if data.get("page_limit") != "" else 10
    else:
        logger.info(f"Received Form data for device: {request.form.to_dict()}")
        # Поддержка старого формата для обратной совместимости
        name = request.form.get("name")
        search_engine = request.form.get("search_engine")
        region = request.form.get("region")
        device = request.form.get("device")

        # Преобразуем старые поля в новые
        search_engine_id = (
            1 if search_engine == "yandex" else 2 if search_engine == "google" else None
        )
        device_id = 1 if device == "desktop" else 2 if device == "mobile" else 1
        logger.info(f"Final device_id to be saved: {device_id}")

        # Устанавливаем значения по умолчанию для полей, которые не были переданы в старом формате
        search_type_id = 1  # Значение по умолчанию
        yandex_region_id = None
        location_id = None
        page_limit = None
        if search_engine == "yandex":
            page_limit = request.form.get("yandex_page_limit", 10)
        elif search_engine == "google":
            page_limit = request.form.get("google_page_limit", 10)

    # Проверяем обязательные поля
    # Проверяем обязательные поля
    if not all([name, search_engine_id, device_id]) or (
        yandex_region_id is None and location_id is None
    ):
        if request.is_json:
            return {
                "success": False,
                "message": "Отсутствуют обязательные поля: имя, поисковая система, устройство или регион/локация.",
            }, 400
        else:
            # Для форм-данных может быть другая логика, оставляем как есть или дорабатываем
            return redirect(
                url_for("project_routes.project_detail", project_id=project_id)
            )

    # Логируем полученные значения для отладки
    if LOGGING_ENABLED:
        logger.info(
            f"Получены данные для сохранения: project_id={project_id}, name={name}, search_engine_id={search_engine_id}, search_type_id={search_type_id}, yandex_region_id={yandex_region_id}, location_id={location_id}, device_id={device_id}, page_limit={page_limit}"
        )

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO parsing_variants (project_id, name, search_engine_id, search_type_id, yandex_region_id, location_id, device_id, page_limit)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            project_id,
            name,
            search_engine_id,
            search_type_id,
            yandex_region_id,
            location_id,
            device_id,
            page_limit,
        )
        logger.info(f"Executing SQL: {sql} with params: {params}")
        cursor.execute(sql, params)
        conn.commit()
        new_variant_id = cursor.lastrowid  # Получаем ID созданного варианта
        if LOGGING_ENABLED:
            logger.info(
                f"Создан вариант парсинга ID: {new_variant_id} для проекта ID: {project_id}"
            )
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(f"Ошибка при добавлении варианта парсинга: {str(e)}")
        if request.is_json:
            return {"success": False, "message": "Ошибка при сохранении варианта"}, 500
        else:
            return redirect(
                url_for("project_routes.project_detail", project_id=project_id)
            )
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    if request.is_json:
        return {
            "success": True,
            "message": "Вариант успешно добавлен",
            "variant_id": new_variant_id,
        }, 201
    else:
        return redirect(url_for("project_routes.project_detail", project_id=project_id))


@project_bp.route("/variants/<int:variant_id>/delete", methods=["POST"])
@login_required
def delete_parsing_variant(variant_id):
    """
    Удаление варианта парсинга по его ID.
    Использует модель ParsingVariant для выполнения операции.
    """
    from app.models import ParsingVariant
    from app.db.database import (
        get_db_connection,
    )  # Импортируем функцию получения соединения

    # Получаем объект варианта
    parsing_variant_obj = ParsingVariant.get_by_id(variant_id)
    if not parsing_variant_obj:
        if request.is_json:
            return {"success": False, "message": "Вариант парсинга не найден"}, 404
        flash("Вариант парсинга не найден", "error")
        return redirect(url_for("project_routes.project_list"))

    # Проверяем права на проект (через проект, связанный с вариантом)
    if not current_user.is_authenticated:
        logger.error("Попытка удаления варианта неавторизованным пользователем")
        if request.is_json:
            return {"success": False, "message": "Требуется авторизация"}, 401
        return redirect(url_for("auth.login"))

    project_id = parsing_variant_obj.project_id
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, user_id FROM projects WHERE id = %s", (project_id,))
        project_owner = cursor.fetchone()
        cursor.close()

        if not project_owner:
            logger.warning(
                f"Проект {project_id} не найден при попытке удаления варианта"
            )
            if request.is_json:
                return {"success": False, "message": "Проект не найден"}, 404
            flash("Проект не найден", "error")
            return redirect(url_for("project_routes.project_list"))

        if project_owner["user_id"] != current_user.id:
            logger.warning(
                f"Попытка удаления варианта из проекта {project_id} пользователем {current_user.id}, владелец: {project_owner['user_id']}"
            )
            if request.is_json:
                return {"success": False, "message": "Доступ запрещен"}, 403
            flash("Доступ запрещен", "error")
            return redirect(url_for("project_routes.project_list"))

        # Используем метод модели для удаления
        if parsing_variant_obj.delete():
            if request.is_json:
                return {"success": True, "message": "Вариант успешно удален"}
            flash("Вариант парсинга успешно удален.", "success")
        else:
            if request.is_json:
                return {
                    "success": False,
                    "message": "Ошибка при удалении варианта",
                }, 500
            flash("Ошибка при удалении варианта.", "error")

    except Exception as e:
        logger.error(
            f"Ошибка удаления варианта парсинга {variant_id}: {e}", exc_info=True
        )
        if request.is_json:
            return {
                "success": False,
                "message": "Внутренняя ошибка сервера при удалении",
            }, 500
        flash("Внутренняя ошибка сервера при удалении.", "error")
    finally:
        if connection and connection.is_connected():
            connection.close()

    if request.is_json:
        return {"success": True, "message": "Вариант успешно удален"}
    return redirect(url_for("project_routes.project_detail", project_id=project_id))


@project_bp.route("/projects/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project(project_id):
    """
    Удаление проекта по его ID.
    """
    from app.models import Project

    # Получаем проект, проверяя права доступа
    project = Project.get_by_id(project_id)

    if not project:
        flash("Проект не найден.", "error")
        abort(404)

    if project.user_id != current_user.id:
        logger.warning(
            f"Попытка удаления чужого проекта {project_id} пользователем {current_user.id}"
        )
        flash("У вас нет прав на удаление этого проекта.", "error")
        abort(403)

    logger.info(
        f"Пользователь {current_user.id} инициировал удаление проекта {project_id}"
    )
    try:
        if project.delete():
            if LOGGING_ENABLED:
                logger.info(
                    f"Роут: Проект {project_id} успешно удален пользователем {current_user.id}"
                )
            flash("Проект успешно удален.", "success")
        else:
            flash("Не удалось удалить проект.", "error")
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при удалении проекта {project_id}: {e}", exc_info=True
            )
        flash("Произошла ошибка при удалении проекта.", "error")

    return redirect(url_for("project_routes.project_list"))
