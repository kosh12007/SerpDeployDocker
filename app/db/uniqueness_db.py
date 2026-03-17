import logging
import os
import json
from mysql.connector import Error
from .database import create_connection
from app.db_config import LOGGING_ENABLED

logger = logging.getLogger(__name__)

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "uniqueness_db.log")
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
# --- Конец настройки логгера ---


def create_uniqueness_task(task_id, user_id, progress_total, source_text=None):
    """Создает новую запись о задаче в БД."""
    try:
        connection = create_connection()
        if not connection:
            return False
        cursor = connection.cursor()
        query = "INSERT INTO uniqueness_tasks (task_id, user_id, progress_total, status, source_text) VALUES (%s, %s, %s, 'pending', %s)"
        cursor.execute(query, (task_id, user_id, progress_total, source_text))
        connection.commit()
        return True
    except Error as e:
        logger.error(f"Ошибка при создании задачи {task_id}: {e}", exc_info=True)
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def update_uniqueness_task_progress(task_id, progress_current, status="running"):
    """Обновляет текущий прогресс задачи."""
    try:
        connection = create_connection()
        if not connection:
            return False
        cursor = connection.cursor()
        query = "UPDATE uniqueness_tasks SET progress_current = %s, status = %s WHERE task_id = %s"
        cursor.execute(query, (progress_current, status, task_id))
        connection.commit()
        return True
    except Error as e:
        logger.error(
            f"Ошибка при обновлении прогресса задачи {task_id}: {e}", exc_info=True
        )
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def complete_uniqueness_task(task_id, result):
    """Помечает задачу как выполненную и сохраняет результат."""
    try:
        connection = create_connection()
        if not connection:
            return False
        cursor = connection.cursor()
        query = "UPDATE uniqueness_tasks SET status = 'completed', result = %s WHERE task_id = %s"
        cursor.execute(query, (json.dumps(result), task_id))
        connection.commit()
        return True
    except Error as e:
        logger.error(f"Ошибка при завершении задачи {task_id}: {e}", exc_info=True)
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def set_uniqueness_task_error(task_id, error_message):
    """Помечает задачу как ошибочную и возвращает лимиты."""
    try:
        connection = create_connection()
        if not connection:
            return False
        cursor = connection.cursor()
        query = "UPDATE uniqueness_tasks SET status = 'error', error_message = %s WHERE task_id = %s"
        cursor.execute(query, (error_message, task_id))
        connection.commit()

        # Автоматический возврат лимитов
        refund_user_limits(task_id)

        return True
    except Error as e:
        logger.error(f"Ошибка при записи ошибки задачи {task_id}: {e}", exc_info=True)
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def get_uniqueness_task(task_id):
    """Получает информацию о задаче."""
    try:
        connection = create_connection()
        if not connection:
            return None
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM uniqueness_tasks WHERE task_id = %s"
        cursor.execute(query, (task_id,))
        task = cursor.fetchone()
        if task and task["result"]:
            task["result"] = json.loads(task["result"])
        return task
    except Error as e:
        logger.error(f"Ошибка при получении задачи {task_id}: {e}", exc_info=True)
        return None
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def get_user_uniqueness_tasks(user_id, limit=20):
    """Получает список последних задач пользователя."""
    try:
        connection = create_connection()
        if not connection:
            return []
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT task_id, status, progress_current, progress_total, 
                   created_at, result
            FROM uniqueness_tasks 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        cursor.execute(query, (user_id, limit))
        tasks = cursor.fetchall()
        for task in tasks:
            if task["result"]:
                task["result"] = json.loads(task["result"])
        return tasks
    except Error as e:
        logger.error(
            f"Ошибка при получении истории задач для пользователя {user_id}: {e}",
            exc_info=True,
        )
        return []
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def delete_uniqueness_task(task_id, user_id):
    """Удаляет задачу из БД (только если она принадлежит пользователю)."""
    try:
        connection = create_connection()
        if not connection:
            return False
        cursor = connection.cursor()
        query = "DELETE FROM uniqueness_tasks WHERE task_id = %s AND user_id = %s"
        cursor.execute(query, (task_id, user_id))
        connection.commit()
        return cursor.rowcount > 0
    except Error as e:
        logger.error(f"Ошибка при удалении задачи {task_id}: {e}", exc_info=True)
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def reserve_user_limits(user_id, task_id, amount):
    """
    Резервирует (списывает) лимиты у пользователя и записывает их количество в задачу.
    Операция выполняется атомарно.
    """
    try:
        connection = create_connection()
        if not connection:
            return False
        cursor = connection.cursor()

        # 1. Списываем лимиты, только если сумма > 0
        if amount > 0:
            query_deduct = (
                "UPDATE users SET limits = limits - %s WHERE id = %s AND limits >= %s"
            )
            cursor.execute(query_deduct, (amount, user_id, amount))

            if cursor.rowcount == 0:
                logger.warning(
                    f"Недостаточно лимитов у пользователя {user_id} для резервирования {amount}"
                )
                connection.rollback()
                return False
        else:
            # Если сумма 0, просто проверяем существование пользователя
            cursor.execute("SELECT 1 FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return False

        # 2. Обновляем задачу, записывая количество списанных лимитов
        query_task = (
            "UPDATE uniqueness_tasks SET reserved_limits = %s WHERE task_id = %s"
        )
        cursor.execute(query_task, (amount, task_id))

        connection.commit()
        logger.info(
            f"Зарезервировано {amount} лимитов для пользователя {user_id} (задача {task_id})"
        )
        return True
    except Error as e:
        logger.error(
            f"Ошибка при резервировании лимитов для пользователя {user_id}: {e}",
            exc_info=True,
        )
        if connection:
            connection.rollback()
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def refund_user_limits(task_id):
    """
    Возвращает зарезервированные лимиты пользователю при ошибке выполнения задачи.
    Находит пользователя и количество лимитов по ID задачи.
    """
    try:
        connection = create_connection()
        if not connection:
            return False
        cursor = connection.cursor(dictionary=True)

        # 1. Получаем ID пользователя и количество зарезервированных лимитов
        query_get = (
            "SELECT user_id, reserved_limits FROM uniqueness_tasks WHERE task_id = %s"
        )
        cursor.execute(query_get, (task_id,))
        task = cursor.fetchone()

        if not task or not task["user_id"] or task["reserved_limits"] <= 0:
            return False

        user_id = task["user_id"]
        amount = task["reserved_limits"]

        # 2. Возвращаем лимиты пользователю
        query_refund = "UPDATE users SET limits = limits + %s WHERE id = %s"
        cursor.execute(query_refund, (amount, user_id))

        # 3. Обнуляем лимиты в задаче, чтобы предотвратить повторный возврат
        query_clear = (
            "UPDATE uniqueness_tasks SET reserved_limits = 0 WHERE task_id = %s"
        )
        cursor.execute(query_clear, (task_id,))

        connection.commit()
        logger.info(
            f"Возвращено {amount} лимитов пользователю {user_id} (задача {task_id})"
        )
        return True
    except Error as e:
        logger.error(
            f"Ошибка при возврате лимитов для задачи {task_id}: {e}", exc_info=True
        )
        if connection:
            connection.rollback()
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def get_cached_shingles(hashes, shingle_len: int = 4, ttl_days: int = 14):
    """
    Получает данные из кеша для списка хэшей и конкретной длины шингла.
    Возвращает словарь {hash: {found_urls, is_unique}}.
    """
    if not hashes:
        return {}

    try:
        connection = create_connection()
        if not connection:
            return {}
        cursor = connection.cursor(dictionary=True)

        # Дедуплицируем хэши для уменьшения SQL-запроса
        unique_hashes = list(set(hashes))
        if not unique_hashes:
            return {}

        format_strings = ",".join(["%s"] * len(unique_hashes))
        query = f"""
            SELECT shingle_hash, found_urls, is_unique, last_updated 
            FROM shingles_cache 
            WHERE shingle_hash IN ({format_strings})
            AND shingle_len = %s
            AND last_updated >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        params = unique_hashes + [shingle_len, ttl_days]
        cursor.execute(query, params)

        results = {}
        for row in cursor.fetchall():
            results[row["shingle_hash"]] = {
                "found_urls": (
                    json.loads(row["found_urls"]) if row["found_urls"] else []
                ),
                "is_unique": bool(row["is_unique"]),
            }
        return results
    except Error as e:
        logger.error(f"Ошибка при получении кеша шинглов: {e}", exc_info=True)
        return {}
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def update_shingles_cache(shingle_data_list, shingle_len: int = 4):
    """
    Массово обновляет или вставляет результаты поиска в кеш.
    shingle_data_list: Список кортежей (shingle_hash, found_urls_json, is_unique)
    shingle_len: Длина шингла для сохранения контекста
    """
    if not shingle_data_list:
        return False

    try:
        connection = create_connection()
        if not connection:
            return False
        cursor = connection.cursor()

        # Дедуплицируем данные перед вставкой
        unique_data = {}
        for h, urls, unique in shingle_data_list:
            unique_data[h] = (h, shingle_len, urls, unique)

        data_to_insert = list(unique_data.values())

        query = """
            INSERT INTO shingles_cache (shingle_hash, shingle_len, found_urls, is_unique, last_updated)
            VALUES (%s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE 
                found_urls = VALUES(found_urls),
                is_unique = VALUES(is_unique),
                last_updated = NOW()
        """
        cursor.executemany(query, data_to_insert)
        connection.commit()
        return True
    except Error as e:
        logger.error(f"Ошибка при обновлении кеша шинглов: {e}", exc_info=True)
        if connection:
            connection.rollback()
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def save_analytics_record(task_id, user_id, analytics_data):
    """
    Сохраняет запись аналитики в персистентную таблицу uniqueness_analytics.
    Вызывается при завершении каждой задачи проверки уникальности.
    Использует INSERT IGNORE для идемпотентности (дубли по task_id игнорируются).

    Args:
        task_id (str): ID завершённой задачи.
        user_id (int): ID пользователя, запустившего проверку.
        analytics_data (dict): Словарь с метриками проверки:
            - score (float): Процент уникальности
            - total_shingles (int): Всего шинглов в тексте
            - checked_shingles (int): Проверено шинглов
            - non_unique_shingles (int): Неуникальных шинглов
            - cache_hits (int): Попаданий в кеш
            - api_calls (int): Запросов к API
            - limits_spent (int): Потрачено лимитов
            - text_length (int): Длина исходного текста
            - top_urls (list): Список доменов с количеством совпадений [{ "url": "domain", "count": N }, ...]
    """
    try:
        connection = create_connection()
        if not connection:
            return False
        cursor = connection.cursor()

        # 1. Основная запись аналитики
        query = """
            INSERT IGNORE INTO uniqueness_analytics 
                (task_id, user_id, score, total_shingles, checked_shingles, 
                 non_unique_shingles, cache_hits, api_calls, limits_spent, text_length)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(
            query,
            (
                task_id,
                user_id,
                analytics_data.get("score", 0),
                analytics_data.get("total_shingles", 0),
                analytics_data.get("checked_shingles", 0),
                analytics_data.get("non_unique_shingles", 0),
                analytics_data.get("cache_hits", 0),
                analytics_data.get("api_calls", 0),
                analytics_data.get("limits_spent", 0),
                analytics_data.get("text_length", 0),
            ),
        )

        # 2. Запись статистики по доменам-дубликатам
        top_urls = analytics_data.get("top_urls", [])
        if top_urls:
            domain_query = """
                INSERT INTO uniqueness_source_domains (task_id, domain, match_count)
                VALUES (%s, %s, %s)
            """
            from urllib.parse import urlparse

            domain_batch = []
            for item in top_urls:
                # url может быть как домен, так и полный URL (в зависимости от того, как придет из checker.py)
                url = item.get("url", "")
                if url.startswith("http"):
                    domain = urlparse(url).netloc
                else:
                    domain = url

                if domain:
                    domain_batch.append((task_id, domain, item.get("count", 0)))

            if domain_batch:
                cursor.executemany(domain_query, domain_batch)

        connection.commit()
        logger.info(f"Сохранена аналитика и статистика доменов для задачи {task_id}")
        return True
    except Error as e:
        logger.error(
            f"Ошибка при сохранении аналитики для задачи {task_id}: {e}", exc_info=True
        )
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def get_uniqueness_analytics(ttl_days=14):
    """
    Получает аналитику по проверкам уникальности из персистентной таблицы uniqueness_analytics
    и состоянию кеша из shingles_cache.
    Данные не зависят от удаления задач или пользователей.
    """
    stats = {
        # Основные метрики (из uniqueness_analytics)
        "total_tasks": 0,
        "total_shingles_checked": 0,
        "total_limits_paid": 0,
        "total_limits_saved": 0,
        "cache_hit_rate": 0,
        # Новые метрики
        "avg_score": 0,
        "total_api_calls": 0,
        "total_cache_hits": 0,
        "total_text_length": 0,
        "checks_today": 0,
        "checks_this_week": 0,
        # Метрики кеша (из shingles_cache)
        "cache_total_count": 0,
        "cache_active_count": 0,
        "cache_expired_count": 0,
        # Списки
        "top_domains": [],
        "top_users": [],
    }

    try:
        connection = create_connection()
        if not connection:
            return stats
        cursor = connection.cursor(dictionary=True)

        # 1. Общая статистика из персистентной таблицы uniqueness_analytics
        cursor.execute(
            """
            SELECT 
                COUNT(*) as tasks_count,
                COALESCE(SUM(checked_shingles), 0) as shingles_total,
                COALESCE(SUM(limits_spent), 0) as paid_total,
                COALESCE(ROUND(AVG(score), 1), 0) as avg_score,
                COALESCE(SUM(api_calls), 0) as total_api,
                COALESCE(SUM(cache_hits), 0) as total_cache,
                COALESCE(SUM(text_length), 0) as total_text_len
            FROM uniqueness_analytics
        """
        )
        task_stats = cursor.fetchone()
        if task_stats and task_stats["tasks_count"] > 0:
            stats["total_tasks"] = task_stats["tasks_count"]
            stats["total_shingles_checked"] = int(task_stats["shingles_total"])
            stats["total_limits_paid"] = int(task_stats["paid_total"])
            stats["avg_score"] = float(task_stats["avg_score"])
            stats["total_api_calls"] = int(task_stats["total_api"])
            stats["total_cache_hits"] = int(task_stats["total_cache"])
            stats["total_text_length"] = int(task_stats["total_text_len"])

            # Расчёт сэкономленных лимитов: кеш-хиты — это запросы, которые не ушли в API
            stats["total_limits_saved"] = stats["total_cache_hits"]

            # Расчёт эффективности кеша
            total_requests = stats["total_api_calls"] + stats["total_cache_hits"]
            if total_requests > 0:
                stats["cache_hit_rate"] = round(
                    (stats["total_cache_hits"] / total_requests) * 100, 1
                )

        # 2. Проверок за сегодня и за неделю
        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN DATE(created_at) = CURDATE() THEN 1 ELSE 0 END) as today,
                SUM(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 ELSE 0 END) as week
            FROM uniqueness_analytics
        """
        )
        time_stats = cursor.fetchone()
        if time_stats:
            stats["checks_today"] = int(time_stats["today"] or 0)
            stats["checks_this_week"] = int(time_stats["week"] or 0)

        # 3. Топ пользователей по количеству проверок (для расчёта скидок)
        cursor.execute(
            """
            SELECT 
                ua.user_id,
                COALESCE(u.username, CONCAT('user_', ua.user_id)) as username,
                COUNT(*) as checks_count,
                COALESCE(SUM(ua.limits_spent), 0) as total_spent,
                COALESCE(ROUND(AVG(ua.score), 1), 0) as avg_score
            FROM uniqueness_analytics ua
            LEFT JOIN users u ON ua.user_id = u.id
            WHERE ua.user_id IS NOT NULL
            GROUP BY ua.user_id
            ORDER BY checks_count DESC
            LIMIT 10
        """
        )
        top_users = cursor.fetchall()
        stats["top_users"] = [
            {
                "user_id": row["user_id"],
                "username": row["username"],
                "checks_count": row["checks_count"],
                "total_spent": int(row["total_spent"]),
                "avg_score": float(row["avg_score"]),
            }
            for row in top_users
        ]

        # 4. Статистика по кешу шинглов
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN last_updated >= DATE_SUB(NOW(), INTERVAL %s DAY) THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN last_updated < DATE_SUB(NOW(), INTERVAL %s DAY) THEN 1 ELSE 0 END) as expired
            FROM shingles_cache
        """,
            (ttl_days, ttl_days),
        )
        cache_stats = cursor.fetchone()
        if cache_stats:
            stats["cache_total_count"] = cache_stats["total"] or 0
            stats["cache_active_count"] = cache_stats["active"] or 0
            stats["cache_expired_count"] = cache_stats["expired"] or 0

        # 5. Топ доменов-источников дублей из персистентной таблицы uniqueness_source_domains
        cursor.execute(
            """
            SELECT domain, SUM(match_count) as total_matches
            FROM uniqueness_source_domains
            GROUP BY domain
            ORDER BY total_matches DESC
            LIMIT 10
        """
        )
        domain_rows = cursor.fetchall()
        stats["top_domains"] = [
            {"domain": row["domain"], "count": int(row["total_matches"])}
            for row in domain_rows
        ]

        # Если данных в новой таблице еще нет (например, до запуска backfill),
        # подмешиваем данные из кеша как временное решение
        if not stats["top_domains"]:
            cursor.execute(
                """
                SELECT found_urls 
                FROM shingles_cache 
                WHERE is_unique = 0 
                ORDER BY last_updated DESC 
                LIMIT 2000
            """
            )
            rows = cursor.fetchall()
            domain_counts = {}
            from urllib.parse import urlparse

            for row in rows:
                try:
                    urls = json.loads(row["found_urls"]) if row["found_urls"] else []
                    for url in urls:
                        domain = urlparse(url).netloc
                        if domain:
                            domain_counts[domain] = domain_counts.get(domain, 0) + 1
                except:
                    continue
            sorted_domains = sorted(
                domain_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
            stats["top_domains"] = [
                {"domain": d, "count": c} for d, c in sorted_domains
            ]

        return stats
    except Error as e:
        logger.error(f"Ошибка при получении аналитики уникальности: {e}", exc_info=True)
        return stats
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
