from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import logging
import os
from .db.database import create_connection
from mysql.connector import Error
from . import login_manager
from app.db_config import LOGGING_ENABLED

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "models.log")
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
    else:
        logger = logging.getLogger(__name__)
        logger.disabled = True
# --- Конец настройки логгера ---


class User(UserMixin):
    def __init__(
        self,
        id,
        username,
        email,
        password_hash,
        limits=0,
        is_admin=False,
        is_super_admin=False,
    ):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.limits = limits
        self.is_admin = is_admin
        self.is_super_admin = is_super_admin

    @staticmethod
    def get_by_id(user_id):
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM users WHERE id = %s"
                cursor.execute(query, (user_id,))
                user_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if user_data:
                    return User(
                        id=user_data["id"],
                        username=user_data["username"],
                        email=user_data["email"],
                        password_hash=user_data["password_hash"],
                        limits=user_data.get("limits", 0),
                        is_admin=user_data.get("is_admin", False),
                        is_super_admin=user_data.get("is_super_admin", False),
                    )
        except Error as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка получения пользователя по ID {user_id}: {e}", exc_info=True
                )
        return None

    @staticmethod
    def get_by_username(username):
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM users WHERE username = %s"
                cursor.execute(query, (username,))
                user_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if user_data:
                    return User(
                        id=user_data["id"],
                        username=user_data["username"],
                        email=user_data["email"],
                        password_hash=user_data["password_hash"],
                        limits=user_data.get("limits", 0),
                        is_admin=user_data.get("is_admin", False),
                        is_super_admin=user_data.get("is_super_admin", False),
                    )
        except Error as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка получения пользователя по имени '{username}': {e}",
                    exc_info=True,
                )
        return None

    @staticmethod
    def get_by_email(email):
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM users WHERE email = %s"
                cursor.execute(query, (email,))
                user_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if user_data:
                    return User(
                        id=user_data["id"],
                        username=user_data["username"],
                        email=user_data["email"],
                        password_hash=user_data["password_hash"],
                        limits=user_data.get("limits", 0),
                        is_admin=user_data.get("is_admin", False),
                        is_super_admin=user_data.get("is_super_admin", False),
                    )
        except Error as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка получения пользователя по email '{email}': {e}",
                    exc_info=True,
                )
        return None

    @staticmethod
    def get_by_reset_token(token):
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM users WHERE reset_token = %s AND reset_token_expires > NOW()"
                cursor.execute(query, (token,))
                user_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if user_data:
                    return User(
                        id=user_data["id"],
                        username=user_data["username"],
                        email=user_data["email"],
                        password_hash=user_data["password_hash"],
                        limits=user_data.get("limits", 0),
                        is_admin=user_data.get("is_admin", False),
                        is_super_admin=user_data.get("is_super_admin", False),
                    )
        except Error as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка получения пользователя по токену '{token}': {e}",
                    exc_info=True,
                )
        return None

    @staticmethod
    def create(username, email, password):
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()

                password_hash = generate_password_hash(password)

                # Используем значение по умолчанию для лимитов из конфигурации
                from .db.settings_db import get_setting

                limits = int(get_setting("DEFAULT_USER_LIMITS") or 300)

                query = "INSERT INTO users (username, email, password_hash, limits) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (username, email, password_hash, limits))
                user_id = cursor.lastrowid

                connection.commit()
                cursor.close()
                connection.close()

                return User.get_by_id(user_id)
        except Error as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка создания пользователя '{username}': {e}", exc_info=True
                )
        return None

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def update_last_login(self):
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "UPDATE users SET last_login = NOW() WHERE id = %s"
                cursor.execute(query, (self.id,))
                connection.commit()
                cursor.close()
                connection.close()
        except Error as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка обновления времени входа для пользователя {self.id}: {e}",
                    exc_info=True,
                )

    def generate_reset_token(self):
        token = secrets.token_urlsafe(32)
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "UPDATE users SET reset_token = %s, reset_token_expires = DATE_ADD(NOW(), INTERVAL 1 HOUR) WHERE id = %s"
                cursor.execute(query, (token, self.id))
                connection.commit()
                cursor.close()
                connection.close()
                return token
        except Error as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка генерации токена сброса для пользователя {self.id}: {e}",
                    exc_info=True,
                )
        return None

    def reset_password(self, new_password):
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                password_hash = generate_password_hash(new_password)
                query = "UPDATE users SET password_hash = %s, reset_token = NULL, reset_token_expires = NULL WHERE id = %s"
                cursor.execute(query, (password_hash, self.id))
                connection.commit()
                cursor.close()
                connection.close()
                return True
        except Error as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка сброса пароля для пользователя {self.id}: {e}",
                    exc_info=True,
                )
        return False


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)


class Project:
    """Модель проекта для хранения информации о проектах парсинга."""

    def __init__(
        self, id, user_id, name, url, is_active=True, created_at=None, updated_at=None
    ):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.url = url
        self.is_active = is_active
        self.created_at = created_at
        self.updated_at = updated_at

    @staticmethod
    def create(user_id, name, url, is_active=True):
        """Создает новый проект."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "INSERT INTO projects (user_id, name, url, is_active) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (user_id, name, url, is_active))
                project_id = cursor.lastrowid
                connection.commit()
                cursor.close()
                connection.close()
                return Project.get_by_id(project_id)
        except Error as e:
            logger.error(f"Ошибка создания проекта '{name}': {e}", exc_info=True)
        return None

    @staticmethod
    def get_by_id(project_id):
        """Получает проект по ID."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM projects WHERE id = %s"
                cursor.execute(query, (project_id,))
                project_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if project_data:
                    return Project(
                        id=project_data["id"],
                        user_id=project_data["user_id"],
                        name=project_data["name"],
                        url=project_data["url"],
                        is_active=project_data["is_active"],
                        created_at=project_data["created_at"],
                        updated_at=project_data["updated_at"],
                    )
        except Error as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка получения проекта по ID {project_id}: {e}", exc_info=True
                )
        return None

    @staticmethod
    def get_by_user_id(user_id):
        """Получает все проекты пользователя."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = (
                    "SELECT * FROM projects WHERE user_id = %s ORDER BY created_at DESC"
                )
                cursor.execute(query, (user_id,))
                projects_data = cursor.fetchall()
                cursor.close()
                connection.close()

                projects = []
                for project_data in projects_data:
                    projects.append(
                        Project(
                            id=project_data["id"],
                            user_id=project_data["user_id"],
                            name=project_data["name"],
                            url=project_data["url"],
                            is_active=project_data["is_active"],
                            created_at=project_data["created_at"],
                            updated_at=project_data["updated_at"],
                        )
                    )
                return projects
        except Error as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка получения проектов для пользователя {user_id}: {e}",
                    exc_info=True,
                )
        return []

    def delete(self):
        """Удаляет проект и все связанные данные (каскадное удаление)."""
        if LOGGING_ENABLED:
            logger.info(f"Начало удаления проекта ID: {self.id}")
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()

                # 1. Удаляем результаты позиций через варианты парсинга
                if LOGGING_ENABLED:
                    logger.debug(
                        f"Удаление parsing_position_results для проекта {self.id}"
                    )
                cursor.execute(
                    """
                    DELETE ppr FROM parsing_position_results ppr
                    JOIN parsing_variants pv ON ppr.parsing_variant_id = pv.id
                    WHERE pv.project_id = %s
                """,
                    (self.id,),
                )

                # 2. Удаляем варианты парсинга
                if LOGGING_ENABLED:
                    logger.debug(f"Удаление parsing_variants для проекта {self.id}")
                cursor.execute(
                    "DELETE FROM parsing_variants WHERE project_id = %s", (self.id,)
                )

                # 3. Удаляем запросы
                if LOGGING_ENABLED:
                    logger.debug(f"Удаление queries для проекта {self.id}")
                cursor.execute("DELETE FROM queries WHERE project_id = %s", (self.id,))

                # 4. Удаляем группы запросов
                if LOGGING_ENABLED:
                    logger.debug(f"Удаление query_groups для проекта {self.id}")
                cursor.execute(
                    "DELETE FROM query_groups WHERE project_id = %s", (self.id,)
                )

                # 5. Удаляем сам проект
                if LOGGING_ENABLED:
                    logger.debug(
                        f"Удаление записи проекта {self.id} из таблицы projects"
                    )
                query = "DELETE FROM projects WHERE id = %s"
                cursor.execute(query, (self.id,))

                connection.commit()
                cursor.close()
                connection.close()
                if LOGGING_ENABLED:
                    logger.info(f"Проект {self.id} успешно удален")
                return True
        except Error as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"CRITICAL: Ошибка удаления проекта {self.id}. Детали: {e}",
                    exc_info=True,
                )
            # Если возможно, откатить транзакцию? Но mysql-connector обычно не требует явного rollback если не было commit, но для надежности:
            # if connection and connection.is_connected(): connection.rollback()
        except Exception as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"CRITICAL: Непредвиденная ошибка при удалении проекта {self.id}: {e}",
                    exc_info=True,
                )
        return False

    @staticmethod
    def get_all():
        """Получает все проекты из базы данных."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM projects ORDER BY created_at DESC"
                cursor.execute(query)
                projects_data = cursor.fetchall()
                cursor.close()
                connection.close()

                projects = []
                for project_data in projects_data:
                    projects.append(
                        Project(
                            id=project_data["id"],
                            user_id=project_data["user_id"],
                            name=project_data["name"],
                            url=project_data["url"],
                            is_active=project_data["is_active"],
                            created_at=project_data["created_at"],
                            updated_at=project_data["updated_at"],
                        )
                    )
                return projects
        except Error as e:
            if LOGGING_ENABLED:
                logger.error(f"Ошибка получения всех проектов: {e}", exc_info=True)
        return []

    def update(self, name=None, url=None, is_active=None):
        """Обновляет проект."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                updates = []
                params = []

                if name is not None:
                    updates.append("name = %s")
                    params.append(name)
                if url is not None:
                    updates.append("url = %s")
                    params.append(url)
                if is_active is not None:
                    updates.append("is_active = %s")
                    params.append(is_active)

                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    query = f"UPDATE projects SET {', '.join(updates)} WHERE id = %s"
                    params.append(self.id)
                    cursor.execute(query, params)
                    connection.commit()

                    # Обновляем атрибуты объекта
                    if name is not None:
                        self.name = name
                    if url is not None:
                        self.url = url
                    if is_active is not None:
                        self.is_active = is_active

                cursor.close()
                connection.close()
                return True
        except Error as e:
            if LOGGING_ENABLED:
                logger.error(f"Ошибка обновления проекта {self.id}: {e}", exc_info=True)
        return False

    def __repr__(self):
        return f"<Project {self.name}>"


class QueryGroup:
    """Модель группы запросов."""

    def __init__(self, id, project_id, name, created_at=None):
        self.id = id
        self.project_id = project_id
        self.name = name
        self.created_at = created_at

    @staticmethod
    def create(project_id, name):
        """Создает новую группу запросов."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "INSERT INTO query_groups (project_id, name) VALUES (%s, %s)"
                cursor.execute(query, (project_id, name))
                group_id = cursor.lastrowid
                connection.commit()
                cursor.close()
                connection.close()
                return QueryGroup.get_by_id(group_id)
        except Error as e:
            logger.error(
                f"Ошибка создания группы запросов '{name}': {e}", exc_info=True
            )
        return None

    @staticmethod
    def get_by_id(group_id):
        """Получает группу запросов по ID."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM query_groups WHERE id = %s"
                cursor.execute(query, (group_id,))
                group_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if group_data:
                    return QueryGroup(
                        id=group_data["id"],
                        project_id=group_data["project_id"],
                        name=group_data["name"],
                        created_at=group_data["created_at"],
                    )
        except Error as e:
            logger.error(
                f"Ошибка получения группы запросов по ID {group_id}: {e}", exc_info=True
            )
        return None

    @staticmethod
    def get_by_project_id(project_id):
        """Получает все группы запросов для проекта."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM query_groups WHERE project_id = %s ORDER BY created_at DESC"
                cursor.execute(query, (project_id,))
                groups_data = cursor.fetchall()
                cursor.close()
                connection.close()

                groups = []
                for group_data in groups_data:
                    groups.append(
                        QueryGroup(
                            id=group_data["id"],
                            project_id=group_data["project_id"],
                            name=group_data["name"],
                            created_at=group_data["created_at"],
                        )
                    )
                return groups
        except Error as e:
            logger.error(
                f"Ошибка получения групп запросов для проекта {project_id}: {e}",
                exc_info=True,
            )
        return []

    def update(self, name=None):
        """Обновляет группу запросов."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                if name:
                    query = "UPDATE query_groups SET name = %s WHERE id = %s"
                    cursor.execute(query, (name, self.id))
                    connection.commit()
                    self.name = name
                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(
                f"Ошибка обновления группы запросов {self.id}: {e}", exc_info=True
            )
        return False

    def delete(self):
        """Удаляет группу запросов."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "DELETE FROM query_groups WHERE id = %s"
                cursor.execute(query, (self.id,))
                connection.commit()
                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(
                f"Ошибка удаления группы запросов {self.id}: {e}", exc_info=True
            )
        return False

    @staticmethod
    def get_groups_with_queries(project_id):
        """
        Получает все группы запросов с их ключевыми словами для указанного проекта.
        """
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                # Получаем группы и связанные с ними запросы
                query = """
                    SELECT
                        qg.id,
                        qg.name,
                        q.id as query_id,
                        q.query_text,
                        q.frequency
                    FROM query_groups qg
                    LEFT JOIN queries q ON qg.id = q.query_group_id
                    WHERE qg.project_id = %s
                    ORDER BY qg.name, q.query_text
                """
                cursor.execute(query, (project_id,))
                results = cursor.fetchall()
                cursor.close()
                connection.close()

                # Группируем результаты по группам
                groups_map = {}
                for row in results:
                    group_id = row["id"]
                    if group_id not in groups_map:
                        groups_map[group_id] = {
                            "id": group_id,
                            "name": row["name"],
                            "queries": [],
                            "total_volume": 0,
                        }

                    if row["query_id"]:  # Добавляем запрос, если он существует
                        query_data = {
                            "id": row["query_id"],
                            "name": row["query_text"],
                            "volume": row["frequency"] or 0,
                        }
                        groups_map[group_id]["queries"].append(query_data)
                        groups_map[group_id]["total_volume"] += query_data["volume"]

                return list(groups_map.values())
        except Error as e:
            logger.error(
                f"Ошибка получения групп с запросами для проекта {project_id}: {e}",
                exc_info=True,
            )
            return []

    def __repr__(self):
        return f"<QueryGroup {self.name}>"


class Query:
    """Модель запроса."""

    def __init__(
        self,
        id,
        project_id,
        query_group_id,
        query_text,
        is_active=True,
        created_at=None,
        updated_at=None,
        frequency=0,
    ):
        self.id = id
        self.project_id = project_id
        self.query_group_id = query_group_id
        self.query_text = query_text
        self.is_active = is_active
        self.created_at = created_at
        self.updated_at = updated_at
        self.frequency = frequency

    @staticmethod
    def create(
        project_id, query_text, query_group_id=None, is_active=True, frequency=0
    ):
        """Создает новый запрос."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "INSERT INTO queries (project_id, query_group_id, query_text, is_active, frequency) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(
                    query,
                    (project_id, query_group_id, query_text, is_active, frequency),
                )
                query_id = cursor.lastrowid
                connection.commit()
                cursor.close()
                connection.close()
                return Query.get_by_id(query_id)
        except Error as e:
            logger.error(f"Ошибка создания запроса '{query_text}': {e}", exc_info=True)
        return None

    @staticmethod
    def get_by_id(query_id):
        """Получает запрос по ID."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM queries WHERE id = %s"
                cursor.execute(query, (query_id,))
                query_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if query_data:
                    return Query(
                        id=query_data["id"],
                        project_id=query_data["project_id"],
                        query_group_id=query_data["query_group_id"],
                        query_text=query_data["query_text"],
                        is_active=query_data["is_active"],
                        created_at=query_data["created_at"],
                        updated_at=query_data["updated_at"],
                        frequency=query_data["frequency"],
                    )
        except Error as e:
            logger.error(
                f"Ошибка получения запроса по ID {query_id}: {e}", exc_info=True
            )
        return None

    @staticmethod
    def get_by_project_id(project_id):
        """Получает все запросы для проекта."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM queries WHERE project_id = %s AND is_active = 1 ORDER BY created_at DESC"
                cursor.execute(query, (project_id,))
                queries_data = cursor.fetchall()
                cursor.close()
                connection.close()

                queries = []
                for query_data in queries_data:
                    queries.append(
                        Query(
                            id=query_data["id"],
                            project_id=query_data["project_id"],
                            query_group_id=query_data["query_group_id"],
                            query_text=query_data["query_text"],
                            is_active=query_data["is_active"],
                            created_at=query_data["created_at"],
                            updated_at=query_data["updated_at"],
                            frequency=query_data["frequency"],
                        )
                    )
                return queries
        except Error as e:
            logger.error(
                f"Ошибка получения запросов для проекта {project_id}: {e}",
                exc_info=True,
            )
        return []

    def update(
        self, query_text=None, query_group_id=None, is_active=None, frequency=None
    ):
        """Обновляет запрос."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                updates = []
                params = []

                if query_text is not None:
                    updates.append("query_text = %s")
                    params.append(query_text)
                if query_group_id is not None:
                    updates.append("query_group_id = %s")
                    params.append(query_group_id)
                if is_active is not None:
                    updates.append("is_active = %s")
                    params.append(is_active)
                if frequency is not None:
                    updates.append("frequency = %s")
                    params.append(frequency)

                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    query = f"UPDATE queries SET {', '.join(updates)} WHERE id = %s"
                    params.append(self.id)
                    cursor.execute(query, params)
                    connection.commit()

                    # Обновляем атрибуты объекта
                    if query_text is not None:
                        self.query_text = query_text
                    if query_group_id is not None:
                        self.query_group_id = query_group_id
                    if is_active is not None:
                        self.is_active = is_active
                    if frequency is not None:
                        self.frequency = frequency

                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(f"Ошибка обновления запроса {self.id}: {e}", exc_info=True)
        return False

    def delete(self):
        """Удаляет запрос."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "DELETE FROM queries WHERE id = %s"
                cursor.execute(query, (self.id,))
                connection.commit()
                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(f"Ошибка удаления запроса {self.id}: {e}", exc_info=True)
        return False

    @staticmethod
    def get_unassigned_queries(project_id):
        """
        Получает все запросы без группы для указанного проекта.
        """
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = """
                    SELECT
                        id,
                        query_text,
                        frequency
                    FROM queries
                    WHERE project_id = %s AND query_group_id IS NULL
                    ORDER BY query_text
                """
                cursor.execute(query, (project_id,))
                results = cursor.fetchall()
                cursor.close()
                connection.close()

                queries = []
                for row in results:
                    queries.append(
                        Query(
                            id=row["id"],
                            project_id=project_id,
                            query_group_id=None,
                            query_text=row["query_text"],
                            is_active=True,  # Предполагаем, что они активны
                            frequency=row.get("frequency", 0),
                        )
                    )
                return queries
        except Error as e:
            logger.error(
                f"Ошибка получения запросов без группы для проекта {project_id}: {e}",
                exc_info=True,
            )
            return []

    def __repr__(self):
        return f"<Query {self.query_text}>"


class SearchEngine:
    """Модель поисковой системы."""

    def __init__(self, id, name, api_name, is_active=True):
        self.id = id
        self.name = name
        self.api_name = api_name
        self.is_active = is_active

    @staticmethod
    def create(name, api_name, is_active=True):
        """Создает новую поисковую систему."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "INSERT INTO search_engines (name, api_name, is_active) VALUES (%s, %s, %s)"
                cursor.execute(query, (name, api_name, is_active))
                engine_id = cursor.lastrowid
                connection.commit()
                cursor.close()
                connection.close()
                return SearchEngine.get_by_id(engine_id)
        except Error as e:
            logger.error(
                f"Ошибка создания поисковой системы '{name}': {e}", exc_info=True
            )
        return None

    @staticmethod
    def get_by_id(engine_id):
        """Получает поисковую систему по ID."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM search_engines WHERE id = %s"
                cursor.execute(query, (engine_id,))
                engine_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if engine_data:
                    return SearchEngine(
                        id=engine_data["id"],
                        name=engine_data["name"],
                        api_name=engine_data["api_name"],
                        is_active=engine_data["is_active"],
                    )
        except Error as e:
            logger.error(
                f"Ошибка получения поисковой системы по ID {engine_id}: {e}",
                exc_info=True,
            )
        return None

    @staticmethod
    def get_all_active():
        """Получает все активные поисковые системы."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM search_engines WHERE is_active = 1 ORDER BY name"
                cursor.execute(query)
                engines_data = cursor.fetchall()
                cursor.close()
                connection.close()

                engines = []
                for engine_data in engines_data:
                    engines.append(
                        SearchEngine(
                            id=engine_data["id"],
                            name=engine_data["name"],
                            api_name=engine_data["api_name"],
                            is_active=engine_data["is_active"],
                        )
                    )
                return engines
        except Error as e:
            logger.error(
                f"Ошибка получения активных поисковых систем: {e}", exc_info=True
            )
        return []

    def update(self, name=None, api_name=None, is_active=None):
        """Обновляет поисковую систему."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                updates = []
                params = []

                if name is not None:
                    updates.append("name = %s")
                    params.append(name)
                if api_name is not None:
                    updates.append("api_name = %s")
                    params.append(api_name)
                if is_active is not None:
                    updates.append("is_active = %s")
                    params.append(is_active)

                if updates:
                    query = (
                        f"UPDATE search_engines SET {', '.join(updates)} WHERE id = %s"
                    )
                    params.append(self.id)
                    cursor.execute(query, params)
                    connection.commit()

                    # Обновляем атрибуты объекта
                    if name is not None:
                        self.name = name
                    if api_name is not None:
                        self.api_name = api_name
                    if is_active is not None:
                        self.is_active = is_active

                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(
                f"Ошибка обновления поисковой системы {self.id}: {e}", exc_info=True
            )
        return False

    def delete(self):
        """Удаляет поисковую систему."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "DELETE FROM search_engines WHERE id = %s"
                cursor.execute(query, (self.id,))
                connection.commit()
                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(
                f"Ошибка удаления поисковой системы {self.id}: {e}", exc_info=True
            )
        return False

    def __repr__(self):
        return f"<SearchEngine {self.name}>"


class SearchType:
    """Модель типа поиска."""

    def __init__(self, id, name, search_engine_id, api_parameter):
        self.id = id
        self.name = name
        self.search_engine_id = search_engine_id
        self.api_parameter = api_parameter

    @staticmethod
    def create(name, search_engine_id, api_parameter):
        """Создает новый тип поиска."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "INSERT INTO search_types (name, search_engine_id, api_parameter) VALUES (%s, %s, %s)"
                cursor.execute(query, (name, search_engine_id, api_parameter))
                type_id = cursor.lastrowid
                connection.commit()
                cursor.close()
                connection.close()
                return SearchType.get_by_id(type_id)
        except Error as e:
            logger.error(f"Ошибка создания типа поиска '{name}': {e}", exc_info=True)
        return None

    @staticmethod
    def get_by_id(type_id):
        """Получает тип поиска по ID."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM search_types WHERE id = %s"
                cursor.execute(query, (type_id,))
                type_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if type_data:
                    return SearchType(
                        id=type_data["id"],
                        name=type_data["name"],
                        search_engine_id=type_data["search_engine_id"],
                        api_parameter=type_data["api_parameter"],
                    )
        except Error as e:
            logger.error(
                f"Ошибка получения типа поиска по ID {type_id}: {e}", exc_info=True
            )
        return None

    @staticmethod
    def get_by_search_engine_id(search_engine_id):
        """Получает все типы поиска для поисковой системы."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM search_types WHERE search_engine_id = %s ORDER BY name"
                cursor.execute(query, (search_engine_id,))
                types_data = cursor.fetchall()
                cursor.close()
                connection.close()

                types = []
                for type_data in types_data:
                    types.append(
                        SearchType(
                            id=type_data["id"],
                            name=type_data["name"],
                            search_engine_id=type_data["search_engine_id"],
                            api_parameter=type_data["api_parameter"],
                        )
                    )
                return types
        except Error as e:
            logger.error(
                f"Ошибка получения типов поиска для поисковой системы {search_engine_id}: {e}",
                exc_info=True,
            )
        return []

    def update(self, name=None, search_engine_id=None, api_parameter=None):
        """Обновляет тип поиска."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                updates = []
                params = []

                if name is not None:
                    updates.append("name = %s")
                    params.append(name)
                if search_engine_id is not None:
                    updates.append("search_engine_id = %s")
                    params.append(search_engine_id)
                if api_parameter is not None:
                    updates.append("api_parameter = %s")
                    params.append(api_parameter)

                if updates:
                    query = (
                        f"UPDATE search_types SET {', '.join(updates)} WHERE id = %s"
                    )
                    params.append(self.id)
                    cursor.execute(query, params)
                    connection.commit()

                    # Обновляем атрибуты объекта
                    if name is not None:
                        self.name = name
                    if search_engine_id is not None:
                        self.search_engine_id = search_engine_id
                    if api_parameter is not None:
                        self.api_parameter = api_parameter

                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(f"Ошибка обновления типа поиска {self.id}: {e}", exc_info=True)
        return False

    def delete(self):
        """Удаляет тип поиска."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "DELETE FROM search_types WHERE id = %s"
                cursor.execute(query, (self.id,))
                connection.commit()
                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(f"Ошибка удаления типа поиска {self.id}: {e}", exc_info=True)
        return False

    def __repr__(self):
        return f"<SearchType {self.name}>"


class Device:
    """Модель устройства."""

    def __init__(self, id, name, api_parameter):
        self.id = id
        self.name = name
        self.api_parameter = api_parameter

    @staticmethod
    def create(name, api_parameter):
        """Создает новое устройство."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "INSERT INTO devices (name, api_parameter) VALUES (%s, %s)"
                cursor.execute(query, (name, api_parameter))
                device_id = cursor.lastrowid
                connection.commit()
                cursor.close()
                connection.close()
                return Device.get_by_id(device_id)
        except Error as e:
            logger.error(f"Ошибка создания устройства '{name}': {e}", exc_info=True)
        return None

    @staticmethod
    def get_by_id(device_id):
        """Получает устройство по ID."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM devices WHERE id = %s"
                cursor.execute(query, (device_id,))
                device_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if device_data:
                    return Device(
                        id=device_data["id"],
                        name=device_data["name"],
                        api_parameter=device_data["api_parameter"],
                    )
        except Error as e:
            logger.error(
                f"Ошибка получения устройства по ID {device_id}: {e}", exc_info=True
            )
        return None

    @staticmethod
    def get_all():
        """Получает все устройства."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM devices ORDER BY name"
                cursor.execute(query)
                devices_data = cursor.fetchall()
                cursor.close()
                connection.close()

                devices = []
                for device_data in devices_data:
                    devices.append(
                        Device(
                            id=device_data["id"],
                            name=device_data["name"],
                            api_parameter=device_data["api_parameter"],
                        )
                    )
                return devices
        except Error as e:
            logger.error(f"Ошибка получения всех устройств: {e}", exc_info=True)
        return []

    def update(self, name=None, api_parameter=None):
        """Обновляет устройство."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                updates = []
                params = []

                if name is not None:
                    updates.append("name = %s")
                    params.append(name)
                if api_parameter is not None:
                    updates.append("api_parameter = %s")
                    params.append(api_parameter)

                if updates:
                    query = f"UPDATE devices SET {', '.join(updates)} WHERE id = %s"
                    params.append(self.id)
                    cursor.execute(query, params)
                    connection.commit()

                    # Обновляем атрибуты объекта
                    if name is not None:
                        self.name = name
                    if api_parameter is not None:
                        self.api_parameter = api_parameter

                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(f"Ошибка обновления устройства {self.id}: {e}", exc_info=True)
        return False

    def delete(self):
        """Удаляет устройство."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "DELETE FROM devices WHERE id = %s"
                cursor.execute(query, (self.id,))
                connection.commit()
                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(f"Ошибка удаления устройства {self.id}: {e}", exc_info=True)
        return False

    def __repr__(self):
        return f"<Device {self.name}>"


class ParsingVariant:
    """Модель варианта парсинга."""

    def __init__(
        self,
        id,
        project_id,
        name,
        search_engine_id,
        search_type_id,
        yandex_region_id,
        location_id,
        device_id,
        page_limit=None,
        is_active=True,
        created_at=None,
    ):
        self.id = id
        self.project_id = project_id
        self.name = name
        self.search_engine_id = search_engine_id
        self.search_type_id = search_type_id
        self.yandex_region_id = yandex_region_id
        self.location_id = location_id
        self.device_id = device_id
        self.page_limit = page_limit
        self.is_active = is_active
        self.created_at = created_at

    @staticmethod
    def create(
        project_id,
        name,
        search_engine_id,
        search_type_id,
        yandex_region_id=None,
        location_id=None,
        device_id=None,
        is_active=True,
    ):
        """Создает новый вариант парсинга."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "INSERT INTO parsing_variants (project_id, name, search_engine_id, search_type_id, yandex_region_id, location_id, device_id, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                cursor.execute(
                    query,
                    (
                        project_id,
                        name,
                        search_engine_id,
                        search_type_id,
                        yandex_region_id,
                        location_id,
                        device_id,
                        is_active,
                    ),
                )
                variant_id = cursor.lastrowid
                connection.commit()
                cursor.close()
                connection.close()
                return ParsingVariant.get_by_id(variant_id)
        except Error as e:
            logger.error(
                f"Ошибка создания варианта парсинга '{name}': {e}", exc_info=True
            )
        return None

    @staticmethod
    def get_by_id(variant_id):
        """Получает вариант парсинга по ID с названиями связанных сущностей."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = """
                    SELECT
                        pv.id, pv.project_id, pv.name, pv.search_engine_id, pv.search_type_id,
                        pv.yandex_region_id, pv.location_id, pv.device_id, pv.page_limit, pv.is_active, pv.created_at,
                        se.name as search_engine,
                        se.api_name as search_engine_api_name,
                        st.name as search_type,
                        st.api_parameter as search_type_api_parameter,
                        yr.region_name as region,
                        d.name as device,
                        l.canonical_name as location
                    FROM parsing_variants pv
                    LEFT JOIN search_engines se ON pv.search_engine_id = se.id
                    LEFT JOIN search_types st ON pv.search_type_id = st.id
                    LEFT JOIN yandex_regions yr ON pv.yandex_region_id = yr.region_id
                    LEFT JOIN devices d ON pv.device_id = d.id
                    LEFT JOIN locations l ON pv.location_id = l.criteria_id
                    WHERE pv.id = %s
                """
                cursor.execute(query, (variant_id,))
                variant_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if variant_data:
                    # Создаем объект ParsingVariant с основными атрибутами
                    variant = ParsingVariant(
                        id=variant_data["id"],
                        project_id=variant_data["project_id"],
                        name=variant_data["name"],
                        search_engine_id=variant_data["search_engine_id"],
                        search_type_id=variant_data["search_type_id"],
                        yandex_region_id=variant_data["yandex_region_id"],
                        location_id=variant_data["location_id"],
                        device_id=variant_data["device_id"],
                        page_limit=variant_data.get("page_limit"),
                        is_active=variant_data["is_active"],
                        created_at=variant_data["created_at"],
                    )
                    # Добавляем атрибуты с названиями связанных сущностей для отображения
                    variant.search_engine = variant_data.get("search_engine")
                    variant.search_engine_api_name = variant_data.get(
                        "search_engine_api_name"
                    )
                    variant.search_type = variant_data.get("search_type")
                    variant.api_parameter = variant_data.get(
                        "search_type_api_parameter"
                    )  # Исправлено для консистентности
                    variant.region = variant_data.get("region")
                    variant.device = variant_data.get("device")
                    variant.location = variant_data.get("location")
                    # Добавляем детали типа поиска
                    variant.search_type_details = {
                        "name": variant_data.get("search_type"),
                        "api_parameter": variant_data.get("search_type_api_parameter"),
                    }
                    return variant
        except Error as e:
            logger.error(
                f"Ошибка получения варианта парсинга по ID {variant_id}: {e}",
                exc_info=True,
            )
        return None

    @staticmethod
    def get_by_project_id(project_id):
        """Получает все варианты парсинга для проекта с названиями связанных сущностей."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = """
                    SELECT
                        pv.id, pv.project_id, pv.name, pv.search_engine_id, pv.search_type_id,
                        pv.yandex_region_id, pv.location_id, pv.device_id, pv.page_limit, pv.is_active, pv.created_at,
                        se.name as search_engine,
                        se.api_name as search_engine_api_name,
                        st.name as search_type,
                        st.api_parameter as search_type_api_parameter,
                        yr.region_name as region,
                        d.name as device,
                        l.canonical_name as location
                    FROM parsing_variants pv
                    LEFT JOIN search_engines se ON pv.search_engine_id = se.id
                    LEFT JOIN search_types st ON pv.search_type_id = st.id
                    LEFT JOIN yandex_regions yr ON pv.yandex_region_id = yr.region_id
                    LEFT JOIN devices d ON pv.device_id = d.id
                    LEFT JOIN locations l ON pv.location_id = l.criteria_id
                    WHERE pv.project_id = %s AND pv.is_active = 1
                    ORDER BY pv.created_at DESC
                """
                cursor.execute(query, (project_id,))
                variants_data = cursor.fetchall()
                cursor.close()
                connection.close()

                variants = []
                for variant_data in variants_data:
                    # Создаем объект ParsingVariant с основными атрибутами
                    variant = ParsingVariant(
                        id=variant_data["id"],
                        project_id=variant_data["project_id"],
                        name=variant_data["name"],
                        search_engine_id=variant_data["search_engine_id"],
                        search_type_id=variant_data["search_type_id"],
                        yandex_region_id=variant_data["yandex_region_id"],
                        location_id=variant_data["location_id"],
                        device_id=variant_data["device_id"],
                        page_limit=variant_data.get("page_limit"),
                        is_active=variant_data["is_active"],
                        created_at=variant_data["created_at"],
                    )
                    # Добавляем атрибуты с названиями связанных сущностей для отображения
                    variant.search_engine = variant_data.get("search_engine")
                    variant.search_engine_api_name = variant_data.get(
                        "search_engine_api_name"
                    )
                    variant.search_type = variant_data.get("search_type")
                    variant.api_parameter = variant_data.get(
                        "search_type_api_parameter"
                    )
                    variant.region = variant_data.get("region")
                    variant.device = variant_data.get("device")
                    variant.location = variant_data.get("location")
                    variants.append(variant)
                return variants
        except Error as e:
            logger.error(
                f"Ошибка получения вариантов парсинга для проекта {project_id}: {e}",
                exc_info=True,
            )
        return []

    def update(
        self,
        name=None,
        search_engine_id=None,
        search_type_id=None,
        yandex_region_id=None,
        location_id=None,
        device_id=None,
        is_active=None,
    ):
        """Обновляет вариант парсинга."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                updates = []
                params = []

                if name is not None:
                    updates.append("name = %s")
                    params.append(name)
                if search_engine_id is not None:
                    updates.append("search_engine_id = %s")
                    params.append(search_engine_id)
                if search_type_id is not None:
                    updates.append("search_type_id = %s")
                    params.append(search_type_id)
                if yandex_region_id is not None:
                    updates.append("yandex_region_id = %s")
                    params.append(yandex_region_id)
                if location_id is not None:
                    updates.append("location_id = %s")
                    params.append(location_id)
                if device_id is not None:
                    updates.append("device_id = %s")
                    params.append(device_id)
                if is_active is not None:
                    updates.append("is_active = %s")
                    params.append(is_active)

                if updates:
                    query = f"UPDATE parsing_variants SET {', '.join(updates)} WHERE id = %s"
                    params.append(self.id)
                    cursor.execute(query, params)
                    connection.commit()

                    # Обновляем атрибуты объекта
                    if name is not None:
                        self.name = name
                    if search_engine_id is not None:
                        self.search_engine_id = search_engine_id
                    if search_type_id is not None:
                        self.search_type_id = search_type_id
                    if yandex_region_id is not None:
                        self.yandex_region_id = yandex_region_id
                    if location_id is not None:
                        self.location_id = location_id
                    if device_id is not None:
                        self.device_id = device_id
                    if is_active is not None:
                        self.is_active = is_active

                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(
                f"Ошибка обновления варианта парсинга {self.id}: {e}", exc_info=True
            )
        return False

    def delete(self):
        """Удаляет вариант парсинга и все связанные результаты позиционирования."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()

                # Удаляем сначала связанные результаты позиционирования
                delete_results_query = (
                    "DELETE FROM parsing_position_results WHERE parsing_variant_id = %s"
                )
                cursor.execute(delete_results_query, (self.id,))

                # Затем удаляем сам вариант
                delete_variant_query = "DELETE FROM parsing_variants WHERE id = %s"
                cursor.execute(delete_variant_query, (self.id,))

                connection.commit()
                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(
                f"Ошибка удаления варианта парсинга {self.id} и связанных результатов: {e}",
                exc_info=True,
            )
        return False

    def __repr__(self):
        return f"<ParsingVariant {self.name}>"


class ParsingPositionResult:
    """Модель результата позиционирования."""

    def __init__(
        self,
        id,
        query_id,
        parsing_variant_id,
        position,
        url_found,
        top_10_urls,
        date,
        created_at=None,
    ):
        self.id = id
        self.query_id = query_id
        self.parsing_variant_id = parsing_variant_id
        self.position = position
        self.url_found = url_found
        self.top_10_urls = top_10_urls
        self.date = date
        self.created_at = created_at

    @staticmethod
    def create(query_id, parsing_variant_id, position, url_found, top_10_urls, date):
        """Создает новый результат позиционирования."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "INSERT INTO parsing_position_results (query_id, parsing_variant_id, position, url_found, top_10_urls, date) VALUES (%s, %s, %s, %s, %s, %s)"
                cursor.execute(
                    query,
                    (
                        query_id,
                        parsing_variant_id,
                        position,
                        url_found,
                        top_10_urls,
                        date,
                    ),
                )
                result_id = cursor.lastrowid
                connection.commit()
                cursor.close()
                connection.close()
                return ParsingPositionResult.get_by_id(result_id)
        except Error as e:
            logger.error(
                f"Ошибка создания результата позиционирования: {e}", exc_info=True
            )
        return None

    @staticmethod
    def get_by_id(result_id):
        """Получает результат позиционирования по ID."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM parsing_position_results WHERE id = %s"
                cursor.execute(query, (result_id,))
                result_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if result_data:
                    return ParsingPositionResult(
                        id=result_data["id"],
                        query_id=result_data["query_id"],
                        parsing_variant_id=result_data["parsing_variant_id"],
                        position=result_data["position"],
                        url_found=result_data["url_found"],
                        top_10_urls=result_data["top_10_urls"],
                        date=result_data["date"],
                        created_at=result_data["created_at"],
                    )
        except Error as e:
            logger.error(
                f"Ошибка получения результата позиционирования по ID {result_id}: {e}",
                exc_info=True,
            )
        return None

    @staticmethod
    def get_by_query_and_variant(query_id, parsing_variant_id, limit=None):
        """Получает результаты позиционирования для запроса и варианта парсинга."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM parsing_position_results WHERE query_id = %s AND parsing_variant_id = %s ORDER BY date DESC"
                params = [query_id, parsing_variant_id]
                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                cursor.execute(query, params)
                results_data = cursor.fetchall()
                cursor.close()
                connection.close()

                results = []
                for result_data in results_data:
                    results.append(
                        ParsingPositionResult(
                            id=result_data["id"],
                            query_id=result_data["query_id"],
                            parsing_variant_id=result_data["parsing_variant_id"],
                            position=result_data["position"],
                            url_found=result_data["url_found"],
                            top_10_urls=result_data["top_10_urls"],
                            date=result_data["date"],
                            created_at=result_data["created_at"],
                        )
                    )
                return results
        except Error as e:
            logger.error(
                f"Ошибка получения результатов позиционирования для запроса {query_id} и варианта {parsing_variant_id}: {e}",
                exc_info=True,
            )
        return []

    def update(self, position=None, url_found=None, top_10_urls=None):
        """Обновляет результат позиционирования."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                updates = []
                params = []

                if position is not None:
                    updates.append("position = %s")
                    params.append(position)
                if url_found is not None:
                    updates.append("url_found = %s")
                    params.append(url_found)
                if top_10_urls is not None:
                    updates.append("top_10_urls = %s")
                    params.append(top_10_urls)

                if updates:
                    query = f"UPDATE parsing_position_results SET {', '.join(updates)} WHERE id = %s"
                    params.append(self.id)
                    cursor.execute(query, params)
                    connection.commit()

                    # Обновляем атрибуты объекта
                    if position is not None:
                        self.position = position
                    if url_found is not None:
                        self.url_found = url_found
                    if top_10_urls is not None:
                        self.top_10_urls = top_10_urls

                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(
                f"Ошибка обновления результата позиционирования {self.id}: {e}",
                exc_info=True,
            )
        return False

    def delete(self):
        """Удаляет результат позиционирования."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "DELETE FROM parsing_position_results WHERE id = %s"
                cursor.execute(query, (self.id,))
                connection.commit()
                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(
                f"Ошибка удаления результата позиционирования {self.id}: {e}",
                exc_info=True,
            )
        return False

    def __repr__(self):
        return f"<ParsingPositionResult Query:{self.query_id}, Variant:{self.parsing_variant_id}, Date:{self.date}, Position:{self.position}>"


class YandexRegion:
    """Модель региона Яндекса."""

    def __init__(self, id, region_id, region_name, is_active=True):
        self.id = id
        self.region_id = region_id
        self.region_name = region_name
        self.is_active = is_active

    @staticmethod
    def create(region_id, region_name, is_active=True):
        """Создает новый регион Яндекса."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "INSERT INTO yandex_regions (region_id, region_name, is_active) VALUES (%s, %s, %s)"
                cursor.execute(query, (region_id, region_name, is_active))
                region_id = cursor.lastrowid
                connection.commit()
                cursor.close()
                connection.close()
                return YandexRegion.get_by_id(region_id)
        except Error as e:
            logger.error(
                f"Ошибка создания региона Яндекса '{region_name}' (ID: {region_id}): {e}",
                exc_info=True,
            )
        return None

    @staticmethod
    def get_by_id(db_id):
        """Получает регион Яндекса по ID записи в БД."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM yandex_regions WHERE id = %s"
                cursor.execute(query, (db_id,))
                region_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if region_data:
                    return YandexRegion(
                        id=region_data["id"],
                        region_id=region_data["region_id"],
                        region_name=region_data["region_name"],
                        is_active=region_data["is_active"],
                    )
        except Error as e:
            logger.error(
                f"Ошибка получения региона Яндекса по ID {db_id}: {e}", exc_info=True
            )
        return None

    @staticmethod
    def get_by_region_id(region_id):
        """Получает регион Яндекса по region_id."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM yandex_regions WHERE region_id = %s"
                cursor.execute(query, (region_id,))
                region_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if region_data:
                    return YandexRegion(
                        id=region_data["id"],
                        region_id=region_data["region_id"],
                        region_name=region_data["region_name"],
                        is_active=region_data["is_active"],
                    )
        except Error as e:
            logger.error(
                f"Ошибка получения региона Яндекса по region_id {region_id}: {e}",
                exc_info=True,
            )
        return None

    @staticmethod
    def get_all_active():
        """Получает все активные регионы Яндекса."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM yandex_regions WHERE is_active = 1 ORDER BY region_name"
                cursor.execute(query)
                regions_data = cursor.fetchall()
                cursor.close()
                connection.close()

                regions = []
                for region_data in regions_data:
                    regions.append(
                        YandexRegion(
                            id=region_data["id"],
                            region_id=region_data["region_id"],
                            region_name=region_data["region_name"],
                            is_active=region_data["is_active"],
                        )
                    )
                return regions
        except Error as e:
            logger.error(
                f"Ошибка получения активных регионов Яндекса: {e}", exc_info=True
            )
        return []

    def update(self, region_name=None, is_active=None):
        """Обновляет регион Яндекса."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                updates = []
                params = []

                if region_name is not None:
                    updates.append("region_name = %s")
                    params.append(region_name)
                if is_active is not None:
                    updates.append("is_active = %s")
                    params.append(is_active)

                if updates:
                    query = (
                        f"UPDATE yandex_regions SET {', '.join(updates)} WHERE id = %s"
                    )
                    params.append(self.id)
                    cursor.execute(query, params)
                    connection.commit()

                    # Обновляем атрибуты объекта
                    if region_name is not None:
                        self.region_name = region_name
                    if is_active is not None:
                        self.is_active = is_active

                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(
                f"Ошибка обновления региона Яндекса {self.id}: {e}", exc_info=True
            )
        return False

    def delete(self):
        """Удаляет регион Яндекса."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "DELETE FROM yandex_regions WHERE id = %s"
                cursor.execute(query, (self.id,))
                connection.commit()
                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(
                f"Ошибка удаления региона Яндекса {self.id}: {e}", exc_info=True
            )
        return False

    def __repr__(self):
        return f"<YandexRegion {self.region_name} (ID: {self.region_id})>"


class Location:
    """Модель локации (использует criteria_id как primary key)."""

    def __init__(
        self,
        criteria_id,
        name,
        canonical_name,
        parent_id,
        country_code,
        target_type,
        status,
        is_active=True,
    ):
        self.criteria_id = criteria_id
        self.name = name
        self.canonical_name = canonical_name
        self.parent_id = parent_id
        self.country_code = country_code
        self.target_type = target_type
        self.status = status
        self.is_active = is_active

    @staticmethod
    def create(
        criteria_id,
        name,
        canonical_name=None,
        parent_id=None,
        country_code=None,
        target_type=None,
        status=None,
        is_active=True,
    ):
        """Создает новую локацию."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "INSERT INTO locations (criteria_id, name, canonical_name, parent_id, country_code, target_type, status, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                cursor.execute(
                    query,
                    (
                        criteria_id,
                        name,
                        canonical_name,
                        parent_id,
                        country_code,
                        target_type,
                        status,
                        is_active,
                    ),
                )
                connection.commit()
                cursor.close()
                connection.close()
                return Location.get_by_criteria_id(criteria_id)
        except Error as e:
            logger.error(
                f"Ошибка создания локации '{name}' (criteria_id: {criteria_id}): {e}",
                exc_info=True,
            )
        return None

    @staticmethod
    def get_by_criteria_id(criteria_id):
        """Получает локацию по criteria_id."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM locations WHERE criteria_id = %s"
                cursor.execute(query, (criteria_id,))
                location_data = cursor.fetchone()
                cursor.close()
                connection.close()

                if location_data:
                    return Location(
                        criteria_id=location_data["criteria_id"],
                        name=location_data["name"],
                        canonical_name=location_data["canonical_name"],
                        parent_id=location_data["parent_id"],
                        country_code=location_data["country_code"],
                        target_type=location_data["target_type"],
                        status=location_data["status"],
                        is_active=location_data["is_active"],
                    )
        except Error as e:
            logger.error(
                f"Ошибка получения локации по criteria_id {criteria_id}: {e}",
                exc_info=True,
            )
        return None

    @staticmethod
    def get_by_country_code(country_code):
        """Получает все локации по коду страны."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM locations WHERE country_code = %s AND is_active = 1 ORDER BY name"
                cursor.execute(query, (country_code,))
                locations_data = cursor.fetchall()
                cursor.close()
                connection.close()

                locations = []
                for location_data in locations_data:
                    locations.append(
                        Location(
                            criteria_id=location_data["criteria_id"],
                            name=location_data["name"],
                            canonical_name=location_data["canonical_name"],
                            parent_id=location_data["parent_id"],
                            country_code=location_data["country_code"],
                            target_type=location_data["target_type"],
                            status=location_data["status"],
                            is_active=location_data["is_active"],
                        )
                    )
                return locations
        except Error as e:
            logger.error(
                f"Ошибка получения локаций для страны {country_code}: {e}",
                exc_info=True,
            )
        return []

    @staticmethod
    def search_locations(search_term):
        """Поиск локаций по названию."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT * FROM locations WHERE name LIKE %s AND is_active = 1 ORDER BY name LIMIT 50"
                cursor.execute(query, (f"%{search_term}%",))
                locations_data = cursor.fetchall()
                cursor.close()
                connection.close()

                locations = []
                for location_data in locations_data:
                    locations.append(
                        Location(
                            criteria_id=location_data["criteria_id"],
                            name=location_data["name"],
                            canonical_name=location_data["canonical_name"],
                            parent_id=location_data["parent_id"],
                            country_code=location_data["country_code"],
                            target_type=location_data["target_type"],
                            status=location_data["status"],
                            is_active=location_data["is_active"],
                        )
                    )
                return locations
        except Error as e:
            logger.error(
                f"Ошибка поиска локаций по термину '{search_term}': {e}", exc_info=True
            )
        return []

    def update(
        self,
        name=None,
        canonical_name=None,
        parent_id=None,
        country_code=None,
        target_type=None,
        status=None,
        is_active=None,
    ):
        """Обновляет локацию."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                updates = []
                params = []

                if name is not None:
                    updates.append("name = %s")
                    params.append(name)
                if canonical_name is not None:
                    updates.append("canonical_name = %s")
                    params.append(canonical_name)
                if parent_id is not None:
                    updates.append("parent_id = %s")
                    params.append(parent_id)
                if country_code is not None:
                    updates.append("country_code = %s")
                    params.append(country_code)
                if target_type is not None:
                    updates.append("target_type = %s")
                    params.append(target_type)
                if status is not None:
                    updates.append("status = %s")
                    params.append(status)
                if is_active is not None:
                    updates.append("is_active = %s")
                    params.append(is_active)

                if updates:
                    query = f"UPDATE locations SET {', '.join(updates)} WHERE criteria_id = %s"
                    params.append(self.criteria_id)
                    cursor.execute(query, params)
                    connection.commit()

                    # Обновляем атрибуты объекта
                    if name is not None:
                        self.name = name
                    if canonical_name is not None:
                        self.canonical_name = canonical_name
                    if parent_id is not None:
                        self.parent_id = parent_id
                    if country_code is not None:
                        self.country_code = country_code
                    if target_type is not None:
                        self.target_type = target_type
                    if status is not None:
                        self.status = status
                    if is_active is not None:
                        self.is_active = is_active

                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(
                f"Ошибка обновления локации {self.criteria_id}: {e}", exc_info=True
            )
        return False

    def delete(self):
        """Удаляет локацию."""
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor()
                query = "DELETE FROM locations WHERE criteria_id = %s"
                cursor.execute(query, (self.criteria_id,))
                connection.commit()
                cursor.close()
                connection.close()
                return True
        except Error as e:
            logger.error(
                f"Ошибка удаления локации {self.criteria_id}: {e}", exc_info=True
            )
        return False

    def __repr__(self):
        return f"<Location {self.name} (criteria_id: {self.criteria_id})>"
