# -*- coding: utf-8 -*-
"""
Модуль для парсинга позиций проектов.

Использует единый модуль xmlriver_client для работы с API XmlRiver.
"""
import os
import logging
import time
from app.db_config import LOGGING_ENABLED
from app.xmlriver_client import get_api_credentials, search_xmlriver
from app.positions_parsing.db.operations import (
    update_position_session_status,
    update_position_session_spent_limits,
    save_parsing_position_result,
    increment_position_session_spent_limits,
)
from app.db.database import spend_limit, get_db_connection
from app.models import User
from app.positions_parsing.utils.limits import check_limits_and_calculate_cost

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "positions_parsing_parser.log")
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


def get_engine_name(engine):
    """Возвращает имя поисковой системы по ID или строке"""
    if isinstance(engine, str) and engine.isdigit():
        # engine - это строка с числом (ID)
        from app.models import SearchEngine

        search_engine = SearchEngine.get_by_id(int(engine))
        if search_engine:
            return search_engine.api_name.lower()
        else:
            raise ValueError(
                f"Поисковая система с ID {engine} не найдена в базе данных"
            )
    elif isinstance(engine, int):
        # engine - это число (ID)
        from app.models import SearchEngine

        search_engine = SearchEngine.get_by_id(engine)
        if search_engine:
            return search_engine.api_name.lower()
        else:
            raise ValueError(
                f"Поисковая система с ID {engine} не найдена в базе данных"
            )
    elif isinstance(engine, str):
        # engine - это строка (может быть name или api_name)
        # Ищем поисковую систему по name или api_name в базе данных
        from app.models import SearchEngine

        all_engines = SearchEngine.get_all_active()
        for se in all_engines:
            if se.api_name.lower() == engine.lower():
                return se.api_name.lower()
            if se.name.lower() == engine.lower():
                return se.api_name.lower()
        # Если не найдено в БД, выбрасываем ошибку
        raise ValueError(f"Поисковая система '{engine}' не найдена в базе данных")
    else:
        raise ValueError(f"Неподдерживаемый формат engine: {type(engine)}")


def _build_api_params(
    query,
    engine_name,
    yandex_type,
    yandex_page_limit,
    google_page_limit,
    user,
    key,
    **kwargs,
):
    """
    Строит параметры для запроса к XmlRiver API.

    Args:
        query: Поисковый запрос
        engine_name: Имя поисковой системы ('yandex' или 'google')
        yandex_type: Тип поиска Яндекса ('search_api' или 'live_search')
        yandex_page_limit: Лимит страниц для Яндекса
        google_page_limit: Лимит страниц для Google
        user: Пользователь API
        key: Ключ API
        **kwargs: Дополнительные параметры для API (например, groupby)

    Returns:
        dict: Параметры запроса
    """
    params = {
        "query": query,
        "user": user,
        "key": key,
    }

    # Добавляем дополнительные параметры, если они есть
    if kwargs:
        params.update(kwargs)

    if engine_name == "yandex":
        params.update(
            {
                "engine": "yandex",
                "yandex_type": yandex_type,
                "page_num": 1,
                "page_limit": yandex_page_limit,
            }
        )
    elif engine_name == "google":
        params.update(
            {"engine": "google", "page_num": 1, "page_limit": google_page_limit}
        )
    else:
        raise ValueError(f"Неподдерживаемый движок: {engine_name}")
    if LOGGING_ENABLED:
        logger.info(f"Передаём параметры {params}")

    return params


def _get_base_url(engine_name, yandex_type):
    """
    Возвращает базовый URL для API в зависимости от поисковой системы и типа поиска.

    Args:
        engine_name: Имя поисковой системы ('yandex' или 'google')
        yandex_type: Тип поиска Яндекса ('search_api' или 'live_search')

    Returns:
        str: Базовый URL API
    """
    if engine_name == "yandex":
        if LOGGING_ENABLED:
            logger.info(f"Тип поиска яндекс {yandex_type}")
        if yandex_type == "live":
            return "http://xmlriver.com/search_yandex/xml"
        else:  # search_api
            return "http://xmlriver.com/yandex/xml"
    else:  # google
        return "http://xmlriver.com/search/xml"


def run_positions_parsing_in_thread(
    engine,
    queries,
    domain,
    mode,
    session_id,
    user_id,
    project_id,
    yandex_type="search_api",
    yandex_page_limit=9,
    google_page_limit=10,
):
    """
    Функция для запуска парсинга позиций в отдельном потоке.
    Использует единый модуль xmlriver_client для работы с API.

    Args:
        engine: ID или имя поисковой системы
        queries: Строка с запросами, разделенными переносами строк
        domain: Домен для поиска
        mode: Режим работы ('hosting' или 'local')
        session_id: ID сессии парсинга
        user_id: ID пользователя
        project_id: ID проекта
        yandex_type: Тип поиска Яндекса ('search_api' или 'live_search')
        yandex_page_limit: Лимит страниц для Яндекса
        google_page_limit: Лимит страниц для Google
    """
    if LOGGING_ENABLED:
        logger.info(
            f"Запуск потока парсинга для сессии {session_id}, пользователь {user_id}, проект {project_id}"
        )
        logger.info(
            f"Параметры: engine={engine}, domain={domain}, yandex_type={yandex_type}, yandex_page_limit={yandex_page_limit}, google_page_limit={google_page_limit}"
        )

    # Получаем учетные данные API
    user, key = get_api_credentials()
    if not user or not key:
        if LOGGING_ENABLED:
            logger.error(
                f"Не удалось получить учетные данные API для сессии {session_id}"
            )
        update_position_session_status(session_id, "error")
        return

    # Получаем имя поисковой системы
    try:
        actual_engine_name = get_engine_name(engine)
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(f"Ошибка определения поисковой системы: {e}")
        update_position_session_status(session_id, "error")
        return

    # Получаем лимиты пользователя
    def get_user_limits(user_id):
        """Получает лимиты пользователя."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT limits FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            if row:
                return row[0]
            else:
                raise ValueError(f"Пользователь с ID {user_id} не найден.")
        finally:
            cursor.close()
            conn.close()

    # Рассчитываем стоимость перед началом
    initial_limits = get_user_limits(user_id)
    queries_lines = [line.strip() for line in queries.split("\n") if line.strip()]
    queries_count = len(queries_lines)

    # Определяем глубину парсинга
    depth = yandex_page_limit if actual_engine_name == "yandex" else google_page_limit

    # Рассчитываем общую стоимость
    try:
        total_cost = check_limits_and_calculate_cost(
            user_id=user_id,
            project_id=project_id,
            queries_count=queries_count,
            search_engine_id=engine if isinstance(engine, int) else None,
            depth=depth,
            search_type=yandex_type,
        )
    except ValueError as e:
        if LOGGING_ENABLED:
            logger.error(f"Ошибка расчета стоимости: {e}")
        update_position_session_status(session_id, "error")
        return

    if LOGGING_ENABLED:
        logger.info(
            f"Рассчитанная стоимость для сессии {session_id}: {total_cost}, доступно лимитов: {initial_limits}"
        )

    if initial_limits < total_cost:
        if LOGGING_ENABLED:
            logger.error(
                f"Недостаточно лимитов для сессии {session_id}. Требуется {total_cost}, доступно {initial_limits}"
            )
        update_position_session_status(session_id, "error")
        return

    update_position_session_status(session_id, "in_progress")

    # Получаем базовый URL для API
    base_url = _get_base_url(actual_engine_name, yandex_type)

    results = []
    total_queries = len(queries_lines)
    completed_queries = 0
    actual_spent_limits = 0

    # --- Основной цикл парсинга ---
    for query in queries_lines:
        try:
            if LOGGING_ENABLED:
                logger.info(
                    f"Обработка запроса [{completed_queries + 1}/{total_queries}]: '{query}' для сессии {session_id}"
                )

            # --- Логика для циклического парсинга (Google или Яндекс Live Search) ---
            is_iterative_parsing = actual_engine_name == "google" or (
                actual_engine_name == "yandex" and yandex_type == "live"
            )

            if is_iterative_parsing:
                found_on_page = False
                first_page_top_10 = []
                # Определяем глубину парсинга в зависимости от движка
                page_limit = (
                    google_page_limit
                    if actual_engine_name == "google"
                    else yandex_page_limit
                )

                # Определяем начальную страницу в зависимости от ПС
                start_page = 0 if actual_engine_name == "yandex" else 1

                # Цикл по страницам
                for page_num in range(start_page, page_limit + start_page):
                    if found_on_page:
                        break  # Если позиция найдена, прекращаем поиск

                    if LOGGING_ENABLED:
                        logger.info(
                            f"Парсинг страницы {page_num} для запроса '{query}' (ПС: {actual_engine_name})"
                        )

                    params = _build_api_params(
                        query,
                        actual_engine_name,
                        yandex_type,
                        yandex_page_limit,
                        google_page_limit,
                        user,
                        key,
                    )
                    # API Яндекса использует 'page' для нумерации с 0, Google - 'page_num' с 1.
                    # Но наш xmlriver_client унифицирует это. Будем использовать 'page' для Яндекса.

                    params["page"] = page_num

                    position, url, success, top_10_urls = search_xmlriver(
                        query, user, key, base_url, actual_engine_name, params, domain
                    )

                    # Сохраняем top_10_urls с первой страницы
                    if page_num == start_page and top_10_urls:
                        first_page_top_10 = top_10_urls

                    if success:
                        increment_position_session_spent_limits(session_id, 1)
                        actual_spent_limits += 1
                        if LOGGING_ENABLED:
                            logger.info(
                                f"Успешно спаршена страница {page_num} для '{query}'. Потрачено лимитов: {actual_spent_limits}"
                            )

                        if position is not None:
                            # Корректируем позицию с учетом начальной страницы
                            corrected_position = (page_num - start_page) * 10 + position
                            found_on_page = True
                            # Используем first_page_top_10, так как нам нужен топ только с первой страницы
                            save_parsing_position_result(
                                session_id,
                                query,
                                corrected_position,
                                url,
                                user_id,
                                project_id,
                                first_page_top_10,
                            )
                            if LOGGING_ENABLED:
                                logger.info(
                                    f"Найдена позиция {corrected_position} (исходная: {position}) для '{query}' на странице {page_num}."
                                )

                    time.sleep(1)  # Задержка между запросами к страницам

                if not found_on_page:
                    # Если домен не найден, сохраняем результат с top-10 первой страницы
                    save_parsing_position_result(
                        session_id,
                        query,
                        None,
                        None,
                        user_id,
                        project_id,
                        first_page_top_10,
                    )
                    if LOGGING_ENABLED:
                        logger.info(
                            f"Позиция для '{query}' не найдена в пределах {page_limit} страниц. Сохранен топ-10 с первой страницы."
                        )
            else:  # --- Стандартная логика для других типов поиска (например, Яндекс API) ---

                params = _build_api_params(
                    query,
                    actual_engine_name,
                    yandex_type,
                    yandex_page_limit,
                    google_page_limit,
                    user,
                    key,
                    groupby=100,
                )
                if LOGGING_ENABLED:
                    logger.info(f"Логика парсинга Яндекс API - Параметры: '{params}' ")
                position, url, success, top_10_urls = search_xmlriver(
                    query, user, key, base_url, actual_engine_name, params, domain
                )

                if success:
                    # Для обычного поиска увеличиваем счетчик потраченных лимитов в БД
                    increment_position_session_spent_limits(session_id, 1)
                    actual_spent_limits += 1
                    if LOGGING_ENABLED:
                        logger.info(
                            f"Успешно обработан запрос '{query}', позиция: {position}, URL: {url}"
                        )

                results.append(
                    {
                        "query": query,
                        "position": position,
                        "url": url,
                        "top_10_urls": top_10_urls or [],
                    }
                )
                save_parsing_position_result(
                    session_id,
                    query,
                    position,
                    url,
                    user_id,
                    project_id,
                    top_10_urls or [],
                )

        except Exception as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Критическая ошибка при парсинге запроса '{query}': {e}",
                    exc_info=True,
                )
            results.append(
                {
                    "query": query,
                    "position": None,
                    "url": None,
                    "top_10_urls": [],
                    "error": str(e),
                }
            )
        finally:
            completed_queries += 1
            time.sleep(1)  # Небольшая задержка между запросами

    # Финализация сессии
    # update_position_session_spent_limits(session_id, actual_spent_limits) # Этот вызов больше не нужен, лимиты инкрементируются

    # Определяем финальный статус на основе результатов
    successful_results = [r for r in results if r.get("position") is not None]
    failed_results = [
        r for r in results if r.get("position") is None and r.get("error")
    ]

    # Списываем лимиты с баланса пользователя
    if not spend_limit(user_id, actual_spent_limits):
        if LOGGING_ENABLED:
            logger.error(
                f"Не удалось списать {actual_spent_limits} лимитов с пользователя {user_id} после завершения сессии {session_id}."
            )
        update_position_session_status(session_id, "error")
    else:
        # Определяем финальный статус
        if len(failed_results) == 0:
            # Все запросы обработаны успешно
            final_status = "completed"
        elif len(successful_results) == 0:
            # Все запросы завершились с ошибкой
            final_status = "error"
        else:
            # Частичное завершение - некоторые запросы успешны, некоторые с ошибкой
            final_status = "partial"

        update_position_session_status(session_id, final_status)
        if LOGGING_ENABLED:
            logger.info(
                f"Поток парсинга для сессии {session_id} завершён. Статус: {final_status}, Потрачено лимитов: {actual_spent_limits}, Успешно: {len(successful_results)}/{total_queries}, Ошибок: {len(failed_results)}"
            )
