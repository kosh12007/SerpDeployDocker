# -*- coding: utf-8 -*-
"""
Модуль для выполнения операций с базой данных, связанных с парсингом позиций.
"""
import os
import logging
from app.db_config import LOGGING_ENABLED
from app.db.database import create_connection
from mysql.connector import Error

# --- Настройка логгера ---
if LOGGING_ENABLED:
    # Используем относительные пути для большей переносимости
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "positions_parsing_db.log")

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


def update_position_session_status(session_id, status):
    """Обновляет статус сессии парсинга позиций в таблице parsing_positions_sessions."""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            update_query = """
            UPDATE parsing_positions_sessions
            SET status = %s, completed_at = CASE WHEN %s IN ('completed', 'error', 'partial') THEN NOW() ELSE completed_at END
            WHERE id = %s
            """
            cursor.execute(update_query, (status, status, session_id))
            connection.commit()
            cursor.close()
            connection.close()
            if LOGGING_ENABLED:
                logger.info(
                    f"Статус сессии позиций {session_id} обновлен на '{status}'."
                )
    except Error as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка обновления статуса сессии позиций {session_id}: {e}",
                exc_info=True,
            )


def update_position_session_spent_limits(session_id, spent_limits):
    """Обновляет количество потраченных лимитов для сессии парсинга позиций."""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            query = (
                "UPDATE parsing_positions_sessions SET spent_limits = %s WHERE id = %s"
            )

            # Преобразование session_id в int для безопасности
            session_id_int = int(session_id)

            if LOGGING_ENABLED:
                logger.info(
                    f"Подготовка к обновлению лимитов для сессии {session_id_int} значением {spent_limits}."
                )
            cursor.execute(query, (spent_limits, session_id_int))
            rows_affected = cursor.rowcount
            connection.commit()
            if LOGGING_ENABLED:
                logger.info(
                    f"Для сессии позиций {session_id_int} установлено {spent_limits} потраченных лимитов. Затронуто строк: {rows_affected}."
                )
            cursor.close()
            connection.close()
            if rows_affected == 0 and LOGGING_ENABLED:
                logger.warning(f"Сессия позиций с ID {session_id_int} не найдена.")
    except (ValueError, TypeError) as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка преобразования session_id '{session_id}' в число: {e}",
                exc_info=True,
            )
    except Error as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при обновлении потраченных лимитов для сессии позиций {session_id}: {e}",
                exc_info=True,
            )


def increment_position_session_spent_limits(session_id, amount=1):
    """Атомарно увеличивает количество потраченных лимитов для сессии."""
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            query = "UPDATE parsing_positions_sessions SET spent_limits = spent_limits + %s WHERE id = %s"
            cursor.execute(query, (amount, session_id))
            connection.commit()
            if LOGGING_ENABLED:
                logger.info(
                    f"Счетчик лимитов для сессии {session_id} увеличен на {amount}."
                )
            cursor.close()
            connection.close()
    except Error as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при инкременте лимитов для сессии {session_id}: {e}",
                exc_info=True,
            )


def create_parsing_positions_session(user_id, project_id, variant_id):
    """
    Создает новую сессию парсинга позиций в базе данных.

    Args:
        user_id (int): ID пользователя.
        project_id (int): ID проекта.
        variant_id (int): ID варианта парсинга.

    Returns:
        int: ID созданной сессии или None в случае ошибки.
    """
    from app.db.database import get_db_connection
    import datetime

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO parsing_positions_sessions
            (user_id, project_id, parsing_variant_id, status, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (user_id, project_id, variant_id, "pending", datetime.datetime.now())
        cursor.execute(sql, params)
        conn.commit()
        session_id = cursor.lastrowid
        return session_id
    except Exception as e:
        print(f"Ошибка при создании сессии парсинга позиций: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def get_session_info(session_id):
    """
    Получает информацию о сессии парсинга позиций из таблицы parsing_positions_sessions.

    Args:
        session_id: ID сессии парсинга позиций

    Returns:
        dict: Словарь с информацией о сессии (status, parsing_variant_id, spent_limits и т.д.) или None в случае ошибки
    """
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT id, user_id, project_id, parsing_variant_id, status, 
                       created_at, completed_at, spent_limits
                FROM parsing_positions_sessions 
                WHERE id = %s
            """
            cursor.execute(query, (session_id,))
            result = cursor.fetchone()
            cursor.close()
            connection.close()

            if result:
                return result
            else:
                if LOGGING_ENABLED:
                    logger.error(
                        f"Сессия {session_id} не найдена в таблице parsing_positions_sessions"
                    )
                return None
    except Error as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка получения информации о сессии {session_id}: {e}", exc_info=True
            )
        return None


def get_session_variant_id(session_id):
    """
    Получает parsing_variant_id из сессии парсинга позиций.

    Args:
        session_id: ID сессии парсинга позиций

    Returns:
        int: parsing_variant_id или None в случае ошибки
    """
    session_info = get_session_info(session_id)
    if session_info:
        return session_info.get("parsing_variant_id")
    return None


def get_session_status(session_id):
    """
    Получает статус сессии парсинга позиций.

    Args:
        session_id: ID сессии парсинга позиций

    Returns:
        str: Статус сессии ('pending', 'in_progress', 'completed', 'error', 'partial') или None в случае ошибки
    """
    session_info = get_session_info(session_id)
    if session_info:
        return session_info.get("status")
    return None


def save_parsing_position_result(
    session_id, query_text, position, url, user_id, project_id, top_10_urls=None
):
    """
    Сохраняет результат парсинга позиции в базу данных.

    Структура таблицы parsing_position_results:
    - query_id: ID запроса
    - parsing_variant_id: ID варианта парсинга (получается из сессии)
    - position: Позиция в выдаче
    - url_found: Найденный URL
    - top_10_urls: JSON с топ-10 URL (опционально)
    - date: Дата парсинга (текущая дата)

    Args:
        session_id: ID сессии парсинга позиций
        query_text: Текст поискового запроса
        position: Позиция в выдаче (может быть None)
        url: Найденный URL (может быть None)
        user_id: ID пользователя (не используется напрямую, но может быть полезен для логирования)
        project_id: ID проекта
        top_10_urls: Список URL из топ-10 результатов (опционально)
    """
    import json
    import datetime

    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()

            # Получаем parsing_variant_id из сессии
            variant_id = get_session_variant_id(session_id)
            if not variant_id:
                if LOGGING_ENABLED:
                    logger.error(
                        f"Не удалось получить parsing_variant_id для сессии {session_id}. Результат не сохранен."
                    )
                return

            # Получаем query_id по query_text и project_id
            query_id_query = (
                "SELECT id FROM queries WHERE query_text = %s AND project_id = %s"
            )
            cursor.execute(query_id_query, (query_text, project_id))
            query_id_result = cursor.fetchone()
            if not query_id_result:
                if LOGGING_ENABLED:
                    logger.error(
                        f"Query с текстом '{query_text}' не найден для проекта {project_id}. Результат не сохранен."
                    )
                cursor.close()
                connection.close()
                return
            query_id = query_id_result[0]

            # Подготавливаем данные для сохранения
            url_found = url if url else None
            top_10_urls_json = None
            if top_10_urls:
                try:
                    top_10_urls_json = json.dumps(top_10_urls, ensure_ascii=False)
                except Exception as e:
                    if LOGGING_ENABLED:
                        logger.warning(
                            f"Не удалось сериализовать top_10_urls в JSON: {e}"
                        )

            # Определяем статус результата
            # Если top_10_urls пустой (None или '[]'), считаем это ошибкой парсинга
            status = (
                "error"
                if not top_10_urls_json or top_10_urls_json == "[]"
                else "success"
            )

            # Сохраняем результат в таблицу parsing_position_results
            insert_query = """
                INSERT INTO parsing_position_results
                (query_id, parsing_variant_id, position, url_found, top_10_urls, date, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            current_date = datetime.date.today()
            cursor.execute(
                insert_query,
                (
                    query_id,
                    variant_id,
                    position,
                    url_found,
                    top_10_urls_json,
                    current_date,
                    status,
                ),
            )
            connection.commit()
            cursor.close()
            connection.close()

            if LOGGING_ENABLED:
                logger.info(
                    f"Результат для запроса '{query_text}' (ID: {query_id}) сохранен. Сессия: {session_id}, Вариант: {variant_id}, Позиция: {position}, URL: {url_found}"
                )
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при сохранении результата парсинга для сессии {session_id}: {e}",
                exc_info=True,
            )


def get_failed_queries_for_reparse(variant_id, project_id):
    """
    Получает тексты запросов, которые завершились с ошибкой
    во время последнего парсинга для данного варианта.

    Args:
        variant_id (int): ID варианта парсинга.
        project_id (int): ID проекта.

    Returns:
        list: Список текстов запросов или пустой список.
    """
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Найти последнюю дату парсинга для этого варианта
        cursor.execute(
            """
           SELECT MAX(date) as last_date
           FROM parsing_position_results ppr
           JOIN queries q ON ppr.query_id = q.id
           WHERE ppr.parsing_variant_id = %s AND q.project_id = %s
       """,
            (variant_id, project_id),
        )
        last_date_result = cursor.fetchone()

        if not last_date_result or not last_date_result["last_date"]:
            if LOGGING_ENABLED:
                logger.info(
                    f"Не найдено истории парсинга для варианта {variant_id} в проекте {project_id}."
                )
            return []

        last_date = last_date_result["last_date"]

        # 2. Получить ID запросов, которые завершились с ошибкой в этот день
        cursor.execute(
            """
           SELECT DISTINCT ppr.query_id
           FROM parsing_position_results ppr
           JOIN queries q ON ppr.query_id = q.id
           WHERE ppr.parsing_variant_id = %s
             AND q.project_id = %s
             AND ppr.date = %s
             AND ppr.status = 'error'
       """,
            (variant_id, project_id, last_date),
        )

        failed_query_ids = [row["query_id"] for row in cursor.fetchall()]

        if not failed_query_ids:
            if LOGGING_ENABLED:
                logger.info(
                    f"Не найдено ошибочных запросов для варианта {variant_id} за {last_date}."
                )
            return []

        # 3. Получить тексты этих запросов
        # Используем String join для безопасной вставки списка ID
        query_ids_placeholder = ", ".join(["%s"] * len(failed_query_ids))
        cursor.execute(
            f"""
           SELECT query_text FROM queries WHERE id IN ({query_ids_placeholder})
       """,
            tuple(failed_query_ids),
        )

        failed_queries = [row["query_text"] for row in cursor.fetchall()]

        if LOGGING_ENABLED:
            logger.info(
                f"Найдено {len(failed_queries)} ошибочных запросов для повторного парсинга."
            )

        return failed_queries

    except Error as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при получении ошибочных запросов для варианта {variant_id}: {e}",
                exc_info=True,
            )
        return []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
