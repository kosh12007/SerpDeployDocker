import logging
import os
from datetime import datetime, date
from ..db.database import create_connection
from mysql.connector import Error
from app.db_config import LOGGING_ENABLED

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "dashboard_service.log")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Отключаем передачу логов в консоль
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
else:
    logger = logging.getLogger(__name__)
    logger.disabled = True


class DashboardService:
    @staticmethod
    def get_stats(
        user_id, project_id=None, variant_id=None, date_from=None, date_to=None
    ):
        """
        Возвращает статистику для пользователя с возможностью фильтрации.

        :param user_id: ID пользователя
        :param project_id: ID проекта (опционально)
        :param variant_id: ID варианта парсинга (опционально)
        :param date_from: Базовая дата для сравнения (с чем сравниваем), формат 'YYYY-MM-DD'
        :param date_to: Целевая дата (что сравниваем), формат 'YYYY-MM-DD'
        :return: Словарь со статистикой, включая разницу между датами если указаны обе
        """
        stats = {
            "total_projects": 0,
            "total_queries": 0,
            "unassigned_queries": 0,
            "top_1": 0,
            "top_3": 0,
            "top_10": 0,
            "top_30": 0,
            "top_100": 0,
            "top_1_diff": 0,
            "top_3_diff": 0,
            "top_10_diff": 0,
            "top_30_diff": 0,
            "top_100_diff": 0,
            "avg_position": 0,
            "requests_today": 0,
        }

        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)

                # 1. Кол-во проектов (всегда общее для пользователя)
                cursor.execute(
                    "SELECT COUNT(*) as count FROM projects WHERE user_id = %s",
                    (user_id,),
                )
                stats["total_projects"] = cursor.fetchone()["count"]

                # 2. Кол-во запросов (зависит от project_id)
                query_queries = """
                    SELECT COUNT(*) as count 
                    FROM queries q
                    JOIN projects p ON q.project_id = p.id
                    WHERE p.user_id = %s
                """
                params_queries = [user_id]
                if project_id:
                    query_queries += " AND q.project_id = %s"
                    params_queries.append(project_id)

                cursor.execute(query_queries, tuple(params_queries))
                stats["total_queries"] = cursor.fetchone()["count"]

                # 3. Нераспределенные запросы (зависит от project_id)
                query_unassigned = """
                    SELECT COUNT(*) as count 
                    FROM queries q
                    JOIN projects p ON q.project_id = p.id
                    WHERE p.user_id = %s AND q.query_group_id IS NULL
                """
                params_unassigned = [user_id]
                if project_id:
                    query_unassigned += " AND q.project_id = %s"
                    params_unassigned.append(project_id)

                cursor.execute(query_unassigned, tuple(params_unassigned))
                stats["unassigned_queries"] = cursor.fetchone()["count"]

                # 4. Вспомогательная функция для получения статистики ТОП-ов за дату
                def get_top_stats_for_date(
                    cursor, user_id, project_id, variant_id, target_date
                ):
                    """
                    Получает статистику ТОП-ов.
                    Если target_date указана - берем данные за эту дату.
                    Иначе - берем последние данные по каждому запросу.
                    """
                    if target_date:
                        # Запрос для конкретной даты
                        top_query = """
                            SELECT
                                SUM(CASE WHEN pos = 1 THEN 1 ELSE 0 END) as t1,
                                SUM(CASE WHEN pos <= 3 THEN 1 ELSE 0 END) as t3,
                                SUM(CASE WHEN pos <= 10 THEN 1 ELSE 0 END) as t10,
                                SUM(CASE WHEN pos <= 30 THEN 1 ELSE 0 END) as t30,
                                SUM(CASE WHEN pos <= 100 THEN 1 ELSE 0 END) as t100,
                                AVG(pos) as avg_pos,
                                GROUP_CONCAT(orig_pos) as debug_orig,
                                GROUP_CONCAT(pos) as debug_pos
                            FROM (
                                SELECT ppr.query_id, CAST(TRIM(ppr.position) AS SIGNED) as pos, ppr.position as orig_pos
                                FROM parsing_position_results ppr
                                JOIN (
                                    SELECT query_id, MAX(id) as max_id
                                    FROM parsing_position_results
                                    WHERE date = %s
                        """
                        top_params = [target_date]

                        if variant_id:
                            top_query += " AND parsing_variant_id = %s"
                            top_params.append(variant_id)

                        top_query += """
                                    GROUP BY query_id
                                ) latest ON ppr.id = latest.max_id
                                JOIN queries q ON ppr.query_id = q.id
                                JOIN projects p ON q.project_id = p.id
                                WHERE p.user_id = %s AND ppr.position > 0
                        """
                        top_params.append(user_id)

                        if project_id:
                            top_query += " AND q.project_id = %s"
                            top_params.append(project_id)

                        top_query += ") results"
                    else:
                        # Запрос для последних данных (без учета даты)
                        top_query = """
                            SELECT
                                SUM(CASE WHEN pos = 1 THEN 1 ELSE 0 END) as t1,
                                SUM(CASE WHEN pos <= 3 THEN 1 ELSE 0 END) as t3,
                                SUM(CASE WHEN pos <= 10 THEN 1 ELSE 0 END) as t10,
                                SUM(CASE WHEN pos <= 30 THEN 1 ELSE 0 END) as t30,
                                SUM(CASE WHEN pos <= 100 THEN 1 ELSE 0 END) as t100,
                                AVG(pos) as avg_pos,
                                GROUP_CONCAT(orig_pos) as debug_orig,
                                GROUP_CONCAT(pos) as debug_pos
                            FROM (
                                SELECT ppr.query_id, CAST(TRIM(ppr.position) AS SIGNED) as pos, ppr.position as orig_pos
                                FROM parsing_position_results ppr
                                JOIN (
                                    SELECT query_id, MAX(id) as max_id
                                    FROM parsing_position_results
                        """
                        top_params = []

                        if variant_id:
                            top_query += " WHERE parsing_variant_id = %s"
                            top_params.append(variant_id)

                        top_query += """
                                    GROUP BY query_id
                                ) latest ON ppr.id = latest.max_id
                                JOIN queries q ON ppr.query_id = q.id
                                JOIN projects p ON q.project_id = p.id
                                WHERE p.user_id = %s AND ppr.position > 0
                        """
                        top_params.append(user_id)

                        if project_id:
                            top_query += " AND q.project_id = %s"
                            top_params.append(project_id)

                        top_query += ") results"

                    cursor.execute(top_query, tuple(top_params))
                    result = cursor.fetchone()

                    if LOGGING_ENABLED:
                        logger.debug(
                            f"TOP Stats Query Result for date {target_date}: {result}"
                        )

                    return result

                # 5. Получаем статистику за целевую дату (date_to) или последнюю
                row = get_top_stats_for_date(
                    cursor, user_id, project_id, variant_id, date_to
                )
                if row and row["t1"] is not None:
                    stats["top_1"] = int(row["t1"])
                    stats["top_3"] = int(row["t3"])
                    stats["top_10"] = int(row["t10"])
                    stats["top_30"] = int(row["t30"])
                    stats["top_100"] = int(row["t100"])
                    stats["avg_position"] = (
                        round(float(row["avg_pos"]), 1) if row["avg_pos"] else 0
                    )

                # 6. Рассчитываем разницу, если указаны обе даты
                if date_from and date_to and project_id and variant_id:
                    # Получаем статистику за базовую дату (date_from)
                    from_row = get_top_stats_for_date(
                        cursor, user_id, project_id, variant_id, date_from
                    )

                    if from_row and from_row["t1"] is not None:
                        from_t1 = int(from_row["t1"])
                        from_t3 = int(from_row["t3"])
                        from_t10 = int(from_row["t10"])
                        from_t30 = int(from_row["t30"])
                        from_t100 = int(from_row["t100"])

                        # Разница: целевая дата (date_to) минус базовая (date_from)
                        stats["top_1_diff"] = stats["top_1"] - from_t1
                        stats["top_3_diff"] = stats["top_3"] - from_t3
                        stats["top_10_diff"] = stats["top_10"] - from_t10
                        stats["top_30_diff"] = stats["top_30"] - from_t30
                        stats["top_100_diff"] = stats["top_100"] - from_t100

                # 7. Запросы за сегодня (всегда общее по пользователю)
                today = date.today().strftime("%Y-%m-%d")
                cursor.execute(
                    """
                    SELECT 
                        (SELECT COUNT(*) FROM parsing_sessions WHERE user_id = %s AND DATE(created_at) = %s) +
                        (SELECT COUNT(*) FROM parsing_positions_sessions WHERE user_id = %s AND DATE(created_at) = %s) as count
                """,
                    (user_id, today, user_id, today),
                )
                stats["requests_today"] = cursor.fetchone()["count"]

                cursor.close()
                connection.close()
        except Error as e:
            logger.error(
                f"Ошибка получения статистики дашборда для пользователя {user_id}: {e}"
            )

        return stats

    @staticmethod
    def get_user_projects(user_id):
        """Возвращает список проектов пользователя для выбора в дашборде."""
        projects = []
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute(
                    "SELECT id, name FROM projects WHERE user_id = %s ORDER BY name",
                    (user_id,),
                )
                projects = cursor.fetchall()
                cursor.close()
                connection.close()
        except Error as e:
            logger.error(
                f"Ошибка получения списка проектов для пользователя {user_id}: {e}"
            )
        return projects

    @staticmethod
    def get_recent_activity(user_id, limit=5):
        """Возвращает список последних действий пользователя."""
        activity = []
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                # Объединяем сессии обычного парсинга и позиций
                cursor.execute(
                    """
                    (SELECT 'parsing' as type, domain as target, status, created_at 
                     FROM parsing_sessions 
                     WHERE user_id = %s)
                    UNION ALL
                    (SELECT 'positions' as type, p.name as target, s.status, s.created_at 
                     FROM parsing_positions_sessions s
                     JOIN projects p ON s.project_id = p.id
                     WHERE s.user_id = %s)
                    ORDER BY created_at DESC
                    LIMIT %s
                """,
                    (user_id, user_id, limit),
                )
                activity = cursor.fetchall()
                cursor.close()
                connection.close()
        except Error as e:
            logger.error(f"Ошибка получения активности для пользователя {user_id}: {e}")
        return activity
