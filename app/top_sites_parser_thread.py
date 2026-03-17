# -*- coding: utf-8 -*-
"""
Модуль для асинхронного парсинга ТОП-10 сайтов.

Содержит функцию для запуска парсинга ТОП-10 сайтов в отдельном потоке.
Поддерживает многопоточную обработку запросов через ThreadPoolExecutor.
"""
import os
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from .db.database import create_connection, spend_limit
from .db.settings_db import get_setting
from .models import User
from top_sites_parser import parse_top_sites
from mysql.connector import Error

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "top_sites_parser_thread.log")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# Важно: предотвращаем передачу логов родительским логгерам (в частности, root логгеру)
logger.propagate = False
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


def _process_single_top_query(
    task_id,
    query_info,
    search_engine,
    region,
    device,
    depth,
    yandex_type,
    yandex_page_limit,
    google_page_limit,
    user_id,
    user,
    limits_lock,
):
    """
    Обрабатывает один запрос для парсинга ТОП-сайтов.
    Вынесена для использования в ThreadPoolExecutor.

    Args:
        task_id: ID задачи
        query_info: Словарь {'id': int, 'text': str}
        search_engine: Поисковая система
        region: ID региона
        device: Тип устройства
        depth: Глубина парсинга
        yandex_type: Тип поиска Яндекса
        yandex_page_limit: Лимит страниц для Яндекса
        google_page_limit: Лимит страниц для Google
        user_id: ID пользователя
        user: Объект пользователя (общий между потоками)
        limits_lock: threading.Lock для синхронизации лимитов

    Returns:
        dict: {'completed': bool, 'spent': int} — результат обработки
    """
    query_id = query_info["id"]
    query_text = query_info["text"]
    all_urls_for_query = []
    local_spent = 0

    connection = None
    try:
        # Каждый поток создаёт своё соединение с БД
        connection = create_connection()
        if not connection:
            logger.error(
                f"[Thread-{task_id}] Не удалось подключиться к БД для обработки фразы {query_id}."
            )
            return {"completed": False, "spent": 0}
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE top_sites_queries SET status = 'running' WHERE id = %s", (query_id,)
        )
        connection.commit()

        page_limit = 1
        if search_engine == "google" or (
            search_engine == "yandex" and yandex_type == "live_search"
        ):
            page_limit = (
                google_page_limit if search_engine == "google" else yandex_page_limit
            )

        for page_num in range(page_limit):
            # Потокобезопасная проверка лимитов
            with limits_lock:
                if int(user.limits) < 1:
                    logger.warning(
                        f"[Thread-{task_id}] У пользователя {user_id} закончились лимиты. Прерывание запроса {query_id}."
                    )
                    cursor.execute(
                        "UPDATE top_sites_queries SET status = 'error' WHERE id = %s",
                        (query_id,),
                    )
                    connection.commit()
                    return {"completed": False, "spent": local_spent}

            urls = parse_top_sites(
                query_text,
                search_engine,
                region,
                device,
                depth,
                yandex_type,
                page_num,
                region,
            )

            # Списываем лимит только после успешного запроса
            if urls is not None:
                # Потокобезопасное списание лимитов
                with limits_lock:
                    if spend_limit(user_id, 1):
                        user.limits -= 1
                        local_spent += 1
                        if urls:
                            all_urls_for_query.extend(urls)
                    else:
                        logger.error(
                            f"[Thread-{task_id}] Не удалось списать лимит для пользователя {user_id}. Прерывание запроса {query_id}."
                        )
                        cursor.execute(
                            "UPDATE top_sites_queries SET status = 'error' WHERE id = %s",
                            (query_id,),
                        )
                        connection.commit()
                        return {"completed": False, "spent": local_spent}
            else:
                logger.error(
                    f"[Thread-{task_id}] Ошибка при парсинге запроса {query_id}. Лимит не списан."
                )

            time.sleep(1)

        if not all_urls_for_query:
            cursor.execute(
                "UPDATE top_sites_queries SET status = 'error' WHERE id = %s",
                (query_id,),
            )
            connection.commit()
            return {"completed": False, "spent": local_spent}

        # Убираем дубликаты, сохраняя порядок
        unique_urls = list(dict.fromkeys(all_urls_for_query))

        for i, url in enumerate(unique_urls, 1):
            result_sql = "INSERT INTO top_sites_results (query_id, url, position) VALUES (%s, %s, %s)"
            cursor.execute(result_sql, (query_id, url, i))

        cursor.execute(
            "UPDATE top_sites_queries SET status = 'completed' WHERE id = %s",
            (query_id,),
        )
        connection.commit()
        return {"completed": True, "spent": local_spent}

    except Exception as e:
        logger.error(
            f"[Thread-{task_id}] Ошибка при обработке фразы ID {query_id}: {e}",
            exc_info=True,
        )
        if connection:
            try:
                cursor.execute(
                    "UPDATE top_sites_queries SET status = 'error' WHERE id = %s",
                    (query_id,),
                )
                connection.commit()
            except Exception:
                pass
        return {"completed": False, "spent": local_spent}
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def run_top_sites_parsing_thread(
    task_id,
    queries,
    search_engine,
    region,
    device,
    depth,
    yandex_type,
    yandex_page_limit,
    google_page_limit,
    user_id,
):
    """
    Выполняется в отдельном потоке. Обрабатывает запросы параллельно через ThreadPoolExecutor.
    Списывает лимиты за каждый успешный запрос.

    Args:
        task_id: ID задачи парсинга ТОП-10
        queries: Список словарей с запросами {'id': int, 'text': str}
        search_engine: Поисковая система ('google' или 'yandex')
        region: ID региона/локации
        device: Тип устройства
        depth: Глубина парсинга
        yandex_type: Тип поиска Яндекса ('search_api' или 'live_search')
        yandex_page_limit: Лимит страниц для Яндекса
        google_page_limit: Лимит страниц для Google
        user_id: ID пользователя
    """
    total_queries = len(queries)
    completed_count = 0
    spent_limits = 0

    user = User.get_by_id(user_id)
    if not user:
        logger.error(
            f"[Thread-{task_id}] Не удалось найти пользователя {user_id} для списания лимитов."
        )
        # Обновляем статус основной задачи на 'error'
        try:
            connection = create_connection()
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE top_sites_tasks SET status = 'error' WHERE id = %s", (task_id,)
            )
            connection.commit()
        except Exception as e:
            logger.error(
                f"[Thread-{task_id}] Не удалось обновить статус задачи на 'error': {e}"
            )
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()
        return

    # Получаем количество потоков из настроек
    threads_count = int(get_setting("UNIQUENESS_THREADS") or 5)
    # Ограничиваем количество потоков количеством запросов
    actual_threads = min(threads_count, total_queries)
    # Lock для потокобезопасного доступа к лимитам пользователя
    limits_lock = threading.Lock()

    logger.info(
        f"[Thread-{task_id}] Запуск многопоточного парсинга ТОП-сайтов: {total_queries} запросов в {actual_threads} потоках"
    )

    with ThreadPoolExecutor(max_workers=actual_threads) as executor:
        # Отправляем все запросы в пул потоков
        future_to_query = {}
        for query_info in queries:
            future = executor.submit(
                _process_single_top_query,
                task_id=task_id,
                query_info=query_info,
                search_engine=search_engine,
                region=region,
                device=device,
                depth=depth,
                yandex_type=yandex_type,
                yandex_page_limit=yandex_page_limit,
                google_page_limit=google_page_limit,
                user_id=user_id,
                user=user,
                limits_lock=limits_lock,
            )
            future_to_query[future] = query_info

        # Собираем результаты по мере завершения
        for future in as_completed(future_to_query):
            query_info = future_to_query[future]
            try:
                result = future.result()
                if result["completed"]:
                    completed_count += 1
                spent_limits += result["spent"]
            except Exception as exc:
                logger.error(
                    f"[Thread-{task_id}] Поток для запроса '{query_info['text']}' завершился с ошибкой: {exc}"
                )

    final_status = (
        "completed"
        if completed_count == total_queries
        else "partial" if completed_count > 0 else "error"
    )

    # Логируем итоги задачи
    logger.info(
        f"[Thread-{task_id}] Задача завершена. Обработано: {completed_count}/{total_queries}. Потрачено лимитов: {spent_limits}."
    )

    try:
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE top_sites_tasks SET status = %s, completed_at = NOW(), spent_limits = %s WHERE id = %s",
            (final_status, spent_limits, task_id),
        )
        connection.commit()
    except Exception as e:
        logger.error(
            f"[Thread-{task_id}] Не удалось обновить финальный статус основной задачи: {e}"
        )
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
