# -*- coding: utf-8 -*-
"""
Единый модуль для работы с API XmlRiver.

Этот модуль содержит функции для отправки запросов к XmlRiver API
и получения данных о позициях в поисковой выдаче.
Используется как старым, так и новым функционалом парсинга.
"""
import os
import requests
import logging
import xmltodict
import re
from time import sleep
from urllib.parse import urlparse, parse_qs
from app.db_config import LOGGING_ENABLED

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "xmlriver_client.log")
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
if LOGGING_ENABLED:
    logger.info(f"Логгер для {__name__} настроен.")
# --- Конец настройки логгера ---


def get_api_credentials():
    """
    Извлекает user и key из переменной окружения API_KEY.

    Returns:
        tuple: (user, key) или (None, None) в случае ошибки
    """
    try:
        api_url = os.getenv("API_KEY")
        if not api_url:
            logger.error("API_KEY не найден в переменных окружения")
            return None, None

        parsed_url = urlparse(api_url)
        query_params = parse_qs(parsed_url.query)
        user = query_params.get("user", [None])[0]
        key = query_params.get("key", [None])[0]

        if not user or not key:
            logger.error("Не удалось извлечь user или key из API_KEY")
            return None, None

        return user, key
    except Exception as e:
        logger.error(f"Ошибка извлечения учетных данных API: {e}", exc_info=True)
        return None, None


def get_domain_from_url(url_str):
    """Извлекает чистый домен из URL."""
    if not url_str:
        return ""
    parsed = urlparse(url_str.lower())
    return parsed.netloc.replace("www.", "").rstrip("/")


def parse_text_serp(text, site_url, safe_query):
    """
    Fallback: Парсит только URL из тегов <url> в XML, сохраняя порядок групп.

    Args:
        text: Текст XML ответа
        site_url: URL сайта для поиска
        safe_query: Безопасное имя запроса для логирования

    Returns:
        tuple: (position, found_url)
    """
    # if LOGGING_ENABLED:
    #     logger.info(f"Запуск fallback парсинга текста для сайта: {site_url}")

    urls = re.findall(r"<url>(https?://[^<]+)</url>", text)
    site_domain = get_domain_from_url(site_url)

    # if LOGGING_ENABLED:
    #     logger.info(
    #         f"Fallback: Найдено {len(urls)} URL в тегах <url> для поиска домена '{site_domain}'"
    #     )

    position = None
    found_url = None
    for i, url in enumerate(urls, 1):
        doc_domain = get_domain_from_url(url)
        # if LOGGING_ENABLED:
        #     logger.debug(f"Позиция {i}: URL '{url}' (домен '{doc_domain}')")

        if site_domain == doc_domain:
            position = i
            found_url = url
            if LOGGING_ENABLED:
                logger.info(f"Fallback: Найден домен на позиции {i}: {url}")
            break

    # if LOGGING_ENABLED:
    #     logger.info(f"Fallback завершен: позиция={position}, URL={found_url}")

    return position, found_url


def search_xmlriver(
    query,
    user,
    key,
    base_url,
    engine,
    params,
    site_url,
    retry_attempts=3,
    retry_delay=5,
):
    """
    Получает позицию и URL для одной страницы, с fallback на текст.

    Args:
        query: Поисковый запрос
        user: Пользователь XmlRiver API
        key: Ключ XmlRiver API
        base_url: Базовый URL API
        engine: Поисковая система ('yandex' или 'google')
        params: Параметры запроса
        site_url: URL сайта для поиска
        retry_attempts: Количество попыток при ошибке
        retry_delay: Задержка между попытками в секундах

    Returns:
        tuple: (position, url, success, top_10_urls)
            - position: Позиция сайта в выдаче (None если не найдено)
            - url: URL найденной страницы (None если не найдено)
            - success: True если запрос успешен, False если ошибка
            - top_10_urls: Список URL из топ-10 результатов
    """
    encoded_query = query.replace("&", "%26")
    safe_query = re.sub(r"[^\w\s-]", "", query.lower()).replace(" ", "_")

    # if LOGGING_ENABLED:
    #     logger.info(f"Начало парсинга для запроса: '{query}', движок: {engine}, сайт: {site_url}, страница: {params.get('page', 0)}")

    # Логируем полную ссылку запроса
    full_url = requests.Request("GET", base_url, params=params).prepare().url
    if LOGGING_ENABLED:
        logger.info(f"Полная ссылка запроса: {full_url}")

    for attempt in range(retry_attempts):
        try:
            if LOGGING_ENABLED:
                logger.info(f"Попытка {attempt + 1} для запроса '{query}'")

            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()

            response_text = response.text
            # if LOGGING_ENABLED:
            #     logger.info(
            #         f"HTTP статус: {response.status_code}, Первые 500 символов ответа: {response_text[:500]}"
            #     )

            try:
                # if LOGGING_ENABLED:
                #     logger.debug(f"Попытка парсинга XML для запроса '{query}'")

                data = xmltodict.parse(response_text)

                # if LOGGING_ENABLED:
                #     logger.info(
                #         f"XML структура (ключи верхнего уровня): {list(data.keys())}"
                #     )

                if "error" in data:
                    error_code = data["error"].get("@code", "unknown")
                    if error_code == "15":
                        if LOGGING_ENABLED:
                            logger.info(f"Запрос '{query}': Нет результатов (код 15)")
                        return None, None, True, []
                    else:
                        raise Exception(f"API ошибка: код {error_code}")

                if "yandexsearch" in data:
                    data = data["yandexsearch"]
                    # if LOGGING_ENABLED:
                    #     logger.info("Обнаружен Yandex-формат XML")
                elif "response" in data:
                    data = data
                    if LOGGING_ENABLED:
                        logger.info("Обнаружен Google-формат XML (или другой)")
                else:
                    raise Exception(
                        "Неизвестный формат XML: корневой элемент не 'yandexsearch' или 'response'"
                    )

                position = None
                found_url = None
                groups = (
                    data.get("response", {})
                    .get("results", {})
                    .get("grouping", {})
                    .get("group", [])
                )
                if isinstance(groups, dict):
                    groups = [groups]

                # Извлекаем топ-10 URL для анализа конкурентов
                top_10_urls = []
                for group in groups[:10]:
                    doc = group.get("doc")
                    if doc and isinstance(doc, dict) and doc.get("url"):
                        top_10_urls.append(doc.get("url"))

                # if LOGGING_ENABLED:
                #     logger.info(f"XML-парсинг: Найдено {len(groups)} групп")

                site_domain = get_domain_from_url(site_url)
                for i, group in enumerate(groups, 1):
                    docs = group.get("doc", [])
                    if isinstance(docs, dict):
                        docs = [docs]
                    for doc in docs:
                        doc_url = doc.get("url", "")
                        doc_domain = get_domain_from_url(doc_url)
                        if LOGGING_ENABLED:
                            logger.debug(f"Найден URL: {doc_url}")

                        if site_domain == doc_domain:
                            position = i
                            found_url = doc_url
                            if LOGGING_ENABLED:
                                logger.info(
                                    f"Найдена позиция {position} для домена {site_domain} в группе {i}"
                                )
                            break
                    if position:
                        break

                if position is not None:
                    if LOGGING_ENABLED:
                        logger.info(
                            f"Запрос '{query}' обработан (XML). Позиция: {position}, URL: {found_url}"
                        )
                        logger.info(
                            f"-----------------------------------------------------------------------------------------"
                        )
                    return position, found_url, True, top_10_urls
                else:
                    # if LOGGING_ENABLED:
                    #     logger.warning(
                    #         f"XML-парсинг: Позиция не найдена (пустые группы), переходим к fallback тексту."
                    #     )
                    position, found_url = parse_text_serp(
                        response_text, site_url, safe_query
                    )
                    if LOGGING_ENABLED:
                        logger.info(
                            f"-----------------------------------------------------------------------------------------"
                        )
                    return position, found_url, True, top_10_urls

            except Exception as xml_e:
                if LOGGING_ENABLED:
                    logger.warning(
                        f"XML-парсинг не удался для '{query}': {xml_e}. Используем fallback текст."
                    )
                position, found_url = parse_text_serp(
                    response_text, site_url, safe_query
                )
                if LOGGING_ENABLED:
                    logger.info(
                        f"Запрос '{query}' обработан (fallback текст). Позиция: {position or 'N/A'}, URL: {found_url or 'N/A'}"
                    )
                return position, found_url, True, top_10_urls

        except Exception as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка для запроса '{query}' (попытка {attempt + 1}): {e}"
                )

            if attempt < retry_attempts - 1:
                if LOGGING_ENABLED:
                    logger.info(
                        f"Ожидание {retry_delay} секунд перед повторной попыткой..."
                    )
                sleep(retry_delay)
            continue

    if LOGGING_ENABLED:
        logger.warning(
            f"Не удалось обработать запрос '{query}' после {retry_attempts} попыток"
        )
    return None, None, False, top_10_urls


def get_position_and_url_single_page(
    query, user, key, base_url, engine, params, site_url
):
    """
    Получает позицию и URL для одной страницы (совместимость со старым кодом).

    Args:
        query: Поисковый запрос
        user: Пользователь XmlRiver API
        key: Ключ XmlRiver API
        base_url: Базовый URL API
        engine: Поисковая система
        params: Параметры запроса
        site_url: URL сайта для поиска

    Returns:
        tuple: (position, url, success)
    """
    position, url, success, _ = search_xmlriver(
        query, user, key, base_url, engine, params, site_url
    )
    return position, url, success


def get_live_search_position_looped(
    query, user, key, base_url, params, site_url, yandex_page_limit
):
    """
    Циклически выполняет 'Живой поиск' по страницам для Яндекса.

    Args:
        query: Поисковый запрос
        user: Пользователь XmlRiver API
        key: Ключ XmlRiver API
        base_url: Базовый URL API
        params: Базовые параметры запроса
        site_url: URL сайта для поиска
        yandex_page_limit: Количество страниц для проверки

    Returns:
        tuple: (position, url, success)
    """
    if LOGGING_ENABLED:
        logger.info(
            f"Запуск циклического 'Живого поиска' для Яндекса до страницы {yandex_page_limit}"
        )

    for page in range(yandex_page_limit):
        if LOGGING_ENABLED:
            logger.info(
                f"Проверка страницы {page + 1}/{yandex_page_limit} для запроса '{query}'"
            )

        current_params = params.copy()
        current_params["page"] = page

        # Логируем URL запроса
        request_url = (
            requests.Request("GET", base_url, params=current_params).prepare().url
        )
        if LOGGING_ENABLED:
            logger.info(f"URL запроса к API Yandex Live: {request_url}")

        position, url, success, _ = search_xmlriver(
            query, user, key, base_url, "yandex_live_page", current_params, site_url
        )

        if position is not None:
            if LOGGING_ENABLED:
                logger.info(f"Домен найден на странице {page + 1}. Прерываем поиск.")
            corrected_position = position + (page * 10)
            return corrected_position, url, True

        sleep(1)

    if LOGGING_ENABLED:
        logger.info(f"Домен не найден после проверки {yandex_page_limit} страниц.")
    return None, None, True


def get_google_position_looped(
    query, user, key, base_url, params, site_url, page_limit
):
    """
    Циклически выполняет поиск Google по страницам.

    Args:
        query: Поисковый запрос
        user: Пользователь XmlRiver API
        key: Ключ XmlRiver API
        base_url: Базовый URL API
        params: Базовые параметры запроса
        site_url: URL сайта для поиска
        page_limit: Количество страниц для проверки

    Returns:
        tuple: (position, url, success)
    """
    if LOGGING_ENABLED:
        logger.info(f"Запуск циклического поиска для Google до страницы {page_limit}")

    for page in range(page_limit):
        if LOGGING_ENABLED:
            logger.info(
                f"Проверка страницы {page + 1}/{page_limit} для запроса '{query}'"
            )

        current_params = params.copy()
        # В Google нумерация страниц начинается с 1
        current_params["page"] = page + 1

        # Логируем URL запроса
        request_url = (
            requests.Request("GET", base_url, params=current_params).prepare().url
        )
        if LOGGING_ENABLED:
            logger.info(f"URL запроса к API Google: {request_url}")

        position, url, success, _ = search_xmlriver(
            query, user, key, base_url, "google_page", current_params, site_url
        )

        if position is not None:
            if LOGGING_ENABLED:
                logger.info(f"Домен найден на странице {page + 1}. Прерываем поиск.")
            # Корректируем позицию с учетом номера страницы
            corrected_position = position + (page * 10)
            return corrected_position, url, True

        sleep(1)

    if LOGGING_ENABLED:
        logger.info(f"Домен не найден после проверки {page_limit} страниц.")
    return None, None, True
