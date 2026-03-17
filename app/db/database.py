import mysql.connector
from mysql.connector import Error
import logging
import os
from ..db_config import DB_CONFIG
from ..db_config import LOGGING_ENABLED

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "database.log")
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


def create_connection():
    """Создает подключение к базе данных MySQL"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        logger.debug("Установлено новое соединение с базой данных.")
        return connection
    except Error as e:
        logger.error(f"Ошибка подключения к MySQL: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка подключения к MySQL: {e}", exc_info=True)
        return None


def get_db_connection():
    """Возвращает соединение с базой данных"""
    return create_connection()


def create_tables():
    """Создает таблицы в базе данных, если они не существуют"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()

            create_users_table = """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                reset_token VARCHAR(255) DEFAULT NULL,
                reset_token_expires TIMESTAMP DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT NULL
            )
            """
            cursor.execute(create_users_table)

            create_results_table = """
            CREATE TABLE IF NOT EXISTS parsing_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                query VARCHAR(500) NOT NULL,
                position INT DEFAULT NULL,
                url VARCHAR(1000),
                processed VARCHAR(10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INT DEFAULT NULL,
                INDEX idx_created_at (created_at),
                INDEX idx_user_id (user_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
            cursor.execute(create_results_table)

            create_sessions_table = """
            CREATE TABLE IF NOT EXISTS parsing_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(100) UNIQUE NOT NULL,
                domain VARCHAR(255) NOT NULL,
                engine VARCHAR(50) NOT NULL,
                status ENUM('running', 'completed', 'error') DEFAULT 'running',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP NULL,
                user_id INT DEFAULT NULL,
                INDEX idx_user_id (user_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
            cursor.execute(create_sessions_table)

            connection.commit()
            cursor.close()
            connection.close()
            logger.info("Все таблицы базы данных проверены/созданы успешно")
        else:
            logger.error(
                "Не удалось создать подключение к базе данных для создания таблиц"
            )
    except Error as e:
        logger.error(f"Ошибка создания таблиц: {e}", exc_info=True)


def create_top_sites_tables():
    """Создает таблицы для 'Выгрузки ТОП-10' (top_sites_tasks, top_sites_queries, top_sites_results), если они не существуют."""
    try:
        connection = create_connection()
        if not connection:
            logger.error(
                "Не удалось создать подключение к базе данных для создания таблиц ТОП-10."
            )
            return

        cursor = connection.cursor()

        create_tasks_table = """
        CREATE TABLE IF NOT EXISTS top_sites_tasks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            search_engine VARCHAR(50) NOT NULL,
            region INT NOT NULL,
            yandex_type VARCHAR(50),
            device VARCHAR(50),
            depth INT,
            status ENUM('running', 'completed', 'error') DEFAULT 'running',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
        cursor.execute(create_tasks_table)

        create_queries_table = """
        CREATE TABLE IF NOT EXISTS top_sites_queries (
            id INT AUTO_INCREMENT PRIMARY KEY,
            task_id INT NOT NULL,
            query_text VARCHAR(500) NOT NULL,
            status ENUM('pending', 'running', 'completed', 'error') DEFAULT 'pending',
            FOREIGN KEY (task_id) REFERENCES top_sites_tasks(id) ON DELETE CASCADE
        )
        """
        cursor.execute(create_queries_table)

        create_results_table = """
        CREATE TABLE IF NOT EXISTS top_sites_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            query_id INT NOT NULL,
            url VARCHAR(1000) NOT NULL,
            position INT NOT NULL,
            FOREIGN KEY (query_id) REFERENCES top_sites_queries(id) ON DELETE CASCADE
        )
        """
        cursor.execute(create_results_table)

        connection.commit()
        logger.info("Все таблицы для 'Выгрузки ТОП-10' успешно созданы.")

    except Error as e:
        logger.error(
            f"Ошибка при создании таблиц для 'Выгрузки ТОП-10': {e}", exc_info=True
        )
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def create_locations_table():
    """Создает таблицу локаций, если она не существует."""
    try:
        connection = create_connection()
        if not connection:
            logger.error(
                "Не удалось создать подключение к базе данных для создания таблицы локаций."
            )
            return

        cursor = connection.cursor()
        # Удаляем старую таблицу countries если она есть
        cursor.execute("DROP TABLE IF EXISTS countries")

        create_table_query = """
        CREATE TABLE IF NOT EXISTS locations (
            criteria_id INT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            canonical_name VARCHAR(255),
            parent_id INT,
            country_code VARCHAR(10),
            target_type VARCHAR(50),
            status VARCHAR(20)
        )
        """
        cursor.execute(create_table_query)
        connection.commit()
        logger.info("Таблица 'locations' успешно создана или уже существует.")

    except Error as e:
        logger.error(f"Ошибка при создании таблицы 'locations': {e}", exc_info=True)
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def check_and_add_user_id_column():
    """Проверяет наличие колонки user_id в таблице parsing_sessions и добавляет её при необходимости"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()

            check_column_query = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'parsing_sessions' AND COLUMN_NAME = 'user_id'
            """
            cursor.execute(check_column_query, (DB_CONFIG["database"],))
            result = cursor.fetchone()

            if not result:
                alter_table_query = """
                ALTER TABLE parsing_sessions
                ADD COLUMN user_id INT DEFAULT NULL,
                ADD INDEX idx_user_id (user_id),
                ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                """
                cursor.execute(alter_table_query)

            connection.commit()
            cursor.close()
            connection.close()
    except Error as e:
        logger.error(
            f"Ошибка при проверке и добавлении колонки user_id: {e}", exc_info=True
        )


def update_session_status(session_id, status):
    """Обновляет статус сессии парсинга"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()

            update_query = """
            UPDATE parsing_sessions
            SET status = %s, completed_at = CASE WHEN %s = 'completed' THEN NOW() ELSE completed_at END
            WHERE session_id = %s
            """

            cursor.execute(update_query, (status, status, session_id))
            connection.commit()
            cursor.close()
            connection.close()
            logger.info(f"Статус сессии {session_id} обновлен на '{status}'.")
    except Error as e:
        logger.error(
            f"Ошибка обновления статуса сессии {session_id}: {e}", exc_info=True
        )


def update_session_spent_limits(session_id, spent_limits):
    """Обновляет количество потраченных лимитов для сессии."""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            query = (
                "UPDATE parsing_sessions SET spent_limits = %s WHERE session_id = %s"
            )
            cursor.execute(query, (spent_limits, session_id))
            rows_affected = cursor.rowcount
            connection.commit()
            logger.info(
                f"Для сессии {session_id} установлено {spent_limits} потраченных лимитов. Затронуто строк: {rows_affected}."
            )
            cursor.close()
            connection.close()
            if rows_affected == 0:
                logger.warning(
                    f"Сессия с session_id {session_id} не найдена в таблице parsing_sessions."
                )
    except Error as e:
        logger.error(
            f"Ошибка при обновлении потраченных лимитов для сессии {session_id}: {e}",
            exc_info=True,
        )


def get_results_from_db(session_id):
    """Получает результаты парсинга из базы данных для указанной сессии"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)

            query = """
            SELECT pr.query, pr.position, pr.url, pr.processed
            FROM parsing_results pr
            JOIN session_results sr ON pr.id = sr.result_id
            JOIN parsing_sessions ps ON sr.session_id = ps.session_id
            WHERE sr.session_id = %s
            ORDER BY pr.id
            """

            cursor.execute(query, (session_id,))
            results = cursor.fetchall()

            cursor.close()
            connection.close()

            return results
        return []
    except Error as e:
        logger.error(
            f"Ошибка получения результатов из базы данных для сессии {session_id}: {e}",
            exc_info=True,
        )
        return []


def get_all_sessions_from_db():
    """Получает список всех сессий парсинга из базы данных"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)

            query = """
            SELECT id, session_id, domain, engine, status, created_at, completed_at
            FROM parsing_sessions
            ORDER BY created_at DESC
            """

            cursor.execute(query)
            sessions = cursor.fetchall()

            cursor.close()
            connection.close()

            return sessions
        return []
    except Error as e:
        logger.error(
            f"Ошибка получения списка сессий из базы данных: {e}", exc_info=True
        )
        return []


def get_user_sessions_from_db(user_id):
    """Получает список сессий парсинга конкретного пользователя из базы данных"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)

            query = """
            SELECT id, session_id, domain, engine, status, created_at, completed_at
            FROM parsing_sessions
            WHERE user_id = %s
            ORDER BY created_at DESC
            """

            cursor.execute(query, (user_id,))
            sessions = cursor.fetchall()

            cursor.close()
            connection.close()

            return sessions
        return []
    except Error as e:
        logger.error(
            f"Ошибка получения списка сессий пользователя {user_id} из базы данных: {e}",
            exc_info=True,
        )
        return []


def create_session_result_table():
    """Создает таблицу связи сессий и результатов"""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()

            cursor.execute("SHOW TABLES LIKE 'session_results'")
            result = cursor.fetchone()

            if not result:
                create_table_query = """
                CREATE TABLE session_results (
                    session_id VARCHAR(100),
                    result_id INT,
                    FOREIGN KEY (session_id) REFERENCES parsing_sessions(session_id) ON DELETE CASCADE,
                    FOREIGN KEY (result_id) REFERENCES parsing_results(id) ON DELETE CASCADE,
                    PRIMARY KEY (session_id, result_id)
                )
                """
                cursor.execute(create_table_query)

            connection.commit()
            cursor.close()
            connection.close()
    except Error as e:
        logger.error(f"Ошибка создания таблицы связи: {e}", exc_info=True)


def init_db():
    """Инициализирует базу данных, создавая все необходимые таблицы."""
    create_tables()
    create_top_sites_tables()
    create_session_result_table()
    check_and_add_user_id_column()
    create_locations_table()


def execute_sql_from_file(filepath):
    """Выполняет SQL-скрипт из файла."""
    try:
        connection = create_connection()
        if not connection:
            logger.error(
                f"Не удалось подключиться к базе данных для выполнения скрипта: {filepath}"
            )
            return False, "Ошибка подключения к БД"

        cursor = connection.cursor()
        with open(filepath, "r", encoding="utf-8") as f:
            sql_script = f.read()

        # Разделяем скрипт на отдельные команды
        sql_commands = [cmd.strip() for cmd in sql_script.split(";") if cmd.strip()]

        for command in sql_commands:
            cursor.execute(command)

        connection.commit()
        logger.info(f"SQL-скрипт '{filepath}' успешно выполнен.")
        return True, f"Скрипт '{os.path.basename(filepath)}' успешно выполнен."

    except Error as e:
        logger.error(f"Ошибка выполнения SQL-скрипта '{filepath}': {e}", exc_info=True)
        if connection and connection.is_connected():
            connection.rollback()
        return False, f"Ошибка выполнения SQL: {e}"
    except FileNotFoundError:
        logger.error(f"Файл SQL-скрипта не найден: {filepath}")
        return False, "Файл SQL-скрипта не найден."
    except Exception as e:
        logger.error(
            f"Непредвиденная ошибка при выполнении SQL-скрипта '{filepath}': {e}",
            exc_info=True,
        )
        if connection and connection.is_connected():
            connection.rollback()
        return False, "Непредвиденная ошибка сервера."
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def get_locations(search_query=None, page=1, per_page=30):
    """Получает список локаций с пагинацией и поиском."""
    try:
        connection = create_connection()
        if not connection:
            logger.error(
                "Не удалось подключиться к базе данных для получения списка локаций."
            )
            return []

        cursor = connection.cursor(dictionary=True)

        base_query = "SELECT criteria_id, canonical_name FROM locations"
        params = []

        if search_query:
            base_query += " WHERE canonical_name LIKE %s"
            params.append(f"%{search_query}%")

        base_query += " ORDER BY canonical_name ASC LIMIT %s OFFSET %s"
        offset = (page - 1) * per_page
        params.extend([per_page, offset])

        cursor.execute(base_query, tuple(params))
        locations = cursor.fetchall()

        # Запрос для общего количества записей (для пагинации на клиенте)
        count_query = "SELECT COUNT(criteria_id) as total FROM locations"
        if search_query:
            count_query += " WHERE canonical_name LIKE %s"
            cursor.execute(count_query, (f"%{search_query}%",))
        else:
            cursor.execute(count_query)

        total_count = cursor.fetchone()["total"]

        return {"locations": locations, "total_count": total_count}

    except Error as e:
        logger.error(f"Ошибка при получении списка локаций: {e}", exc_info=True)
        return {"locations": [], "total_count": 0}
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def get_yandex_regions(search_query=None, page=1, per_page=30):
    """Получает список регионов Яндекса с пагинацией и поиском."""
    try:
        connection = create_connection()
        if not connection:
            logger.error(
                "Не удалось подключиться к базе данных для получения регионов Яндекса."
            )
            return {"regions": [], "total_count": 0}

        cursor = connection.cursor(dictionary=True)

        base_query = "SELECT region_id, region_name FROM yandex_regions"
        count_query = "SELECT COUNT(id) as total FROM yandex_regions"
        params = []

        if search_query:
            base_query += " WHERE region_name LIKE %s"
            count_query += " WHERE region_name LIKE %s"
            params.append(f"%{search_query}%")

        base_query += " ORDER BY region_name ASC LIMIT %s OFFSET %s"
        offset = (page - 1) * per_page

        cursor.execute(count_query, tuple(params))
        total_count = cursor.fetchone()["total"]

        params.extend([per_page, offset])
        cursor.execute(base_query, tuple(params))
        regions = cursor.fetchall()

        return {"regions": regions, "total_count": total_count}

    except Error as e:
        logger.error(
            f"Ошибка при получении списка регионов Яндекса: {e}", exc_info=True
        )
        return {"regions": [], "total_count": 0}
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def spend_limit(user_id, amount=1):
    """
    Списывает указанное количество лимитов у пользователя.
    Возвращает True в случае успеха, False в случае неудачи (например, недостаточно лимитов).
    """
    try:
        connection = create_connection()
        if not connection:
            logger.error(
                f"Не удалось подключиться к БД для списания лимитов пользователя {user_id}."
            )
            return False

        cursor = connection.cursor()

        # Используем SELECT ... FOR UPDATE для блокировки строки пользователя
        connection.start_transaction()

        try:
            # Проверяем текущее количество лимитов
            cursor.execute(
                "SELECT limits FROM users WHERE id = %s FOR UPDATE", (user_id,)
            )
            user_limits = cursor.fetchone()

            if user_limits and user_limits[0] >= amount:
                # Списываем лимиты
                update_query = "UPDATE users SET limits = limits - %s WHERE id = %s"
                cursor.execute(update_query, (amount, user_id))
                connection.commit()
                logger.info(f"Списано {amount} лимитов у пользователя {user_id}.")
                return True
            else:
                # Недостаточно лимитов, откатываем транзакцию
                connection.rollback()
                logger.warning(
                    f"У пользователя {user_id} недостаточно лимитов для списания."
                )
                return False
        except Error as e:
            connection.rollback()
            logger.error(
                f"Ошибка транзакции при списании лимитов для пользователя {user_id}: {e}",
                exc_info=True,
            )
            return False
        finally:
            cursor.close()
            connection.close()

    except Error as e:
        logger.error(
            f"Ошибка подключения к БД при списании лимитов для пользователя {user_id}: {e}",
            exc_info=True,
        )
        return False


def get_countries():
    """Получает список всех стран из базы данных."""
    try:
        connection = create_connection()
        if not connection:
            logger.error(
                "Не удалось подключиться к базе данных для получения списка стран."
            )
            return []

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, name FROM countries ORDER BY name ASC")
        countries = cursor.fetchall()
        return countries

    except Error as e:
        logger.error(f"Ошибка при получении списка стран: {e}", exc_info=True)
        return []
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def get_applied_migrations():
    """Получает список уже примененных миграций из таблицы migrations."""
    try:
        connection = create_connection()
        if not connection:
            return []

        cursor = connection.cursor()
        # Убедимся, что таблица миграций существует
        cursor.execute(
            """
           CREATE TABLE IF NOT EXISTS migrations (
               version VARCHAR(255) NOT NULL,
               PRIMARY KEY (version)
           ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
       """
        )

        cursor.execute("SELECT version FROM migrations")
        applied = [row[0] for row in cursor.fetchall()]
        return applied
    except Error as e:
        logger.error(
            f"Ошибка при получении списка примененных миграций: {e}", exc_info=True
        )
        return []
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def mark_migration_as_applied(version):
    """Отмечает миграцию как примененную, добавляя ее в таблицу migrations."""
    try:
        connection = create_connection()
        if not connection:
            return

        cursor = connection.cursor()
        cursor.execute("INSERT INTO migrations (version) VALUES (%s)", (version,))
        connection.commit()
    except Error as e:
        logger.error(
            f"Ошибка при отметке миграции '{version}' как примененной: {e}",
            exc_info=True,
        )
        if connection and connection.is_connected():
            connection.rollback()
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
