# -*- coding: utf-8 -*-
import requests
import xmltodict
import os
from time import sleep
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
import logging
import re

from app.db_config import LOGGING_ENABLED

# --- Настройка логгера ---
LOGGING_ENABLED = True  # True для включения логгирования, или закомментировать чтобы получать глобальные настройки из from app.db_config import LOGGING_ENABLED
if LOGGING_ENABLED:
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "top_sites_parser.log")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.propagate = (
        False  # Изолируем логи, чтобы они не попадали в другие обработчики
    )
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    logger.info(f"Логгер для {__name__} настроен и изолирован.")
# --- Конец настройки логгера ---


# Загрузка настроек из .env
load_dotenv()

# Настройки с fallback значениями
API_URL = os.getenv("API_KEY")
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", 3))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", 10))

# Извлечение user и key из API_URL
try:
    parsed_url = urlparse(API_URL)
    query_params = parse_qs(parsed_url.query)
    USER = query_params.get("user", [None])[0]
    API_KEY = query_params.get("key", [None])[0]
    if not USER or not API_KEY:
        raise ValueError("Не удалось извлечь user или key из API_URL")
except Exception as e:
    print(f"Ошибка: Некорректный API_URL в .env: {e}")
    exit(1)


def get_top_urls_from_response(response_text, depth=10):
    """Извлекает топ URL из XML-ответа API."""
    try:
        data = xmltodict.parse(response_text)
        logger.info(f"XML структура (ключи верхнего уровня): {list(data.keys())}")

        if "error" in data:
            error_code = data["error"].get("@code", "unknown")
            if error_code == "15":
                logger.info(f"Нет результатов (код 15)")
                return []
            else:
                raise Exception(f"API ошибка: код {error_code}")

        if "yandexsearch" in data:
            data = data["yandexsearch"]
            logger.info("Обнаружен Yandex-формат XML")
        elif "response" in data:
            data = data
            logger.info("Обнаружен Google-формат XML (или другой)")
        else:
            raise Exception(
                "Неизвестный формат XML: корневой элемент не 'yandexsearch' или 'response'"
            )

        urls = []
        groups = (
            data.get("response", {})
            .get("results", {})
            .get("grouping", {})
            .get("group", [])
        )
        if isinstance(groups, dict):
            groups = [groups]
        logger.info(f"XML-парсинг: Найдено {len(groups)} групп")

        for i, group in enumerate(groups, 1):
            if len(urls) >= depth:
                break
            docs = group.get("doc", [])
            if isinstance(docs, dict):
                docs = [docs]
            for doc in docs:
                if len(urls) >= depth:
                    break
                doc_url = doc.get("url", "")
                if doc_url:
                    urls.append(doc_url)
                    logger.debug(f"Найден URL: {doc_url}")

        # Если XML-парсинг не дал результатов, используем fallback
        if not urls:
            logger.warning("XML-парсинг не дал результатов, используем fallback текст.")
            urls = re.findall(r"<url>(https?://[^<]+)</url>", response_text)
            urls = urls[:depth]

        logger.info(f"Найдено {len(urls)} URL из XML-ответа")
        return urls
    except Exception as xml_e:
        logger.warning(f"XML-парсинг не удался: {xml_e}. Используем fallback текст.")
        urls = re.findall(r"<url>(https?://[^<]+)</url>", response_text)
        urls = urls[:depth]
        logger.info(f"Найдено {len(urls)} URL из fallback текста")
        return urls


def make_search_request(query, base_url, params, depth):
    """Выполняет один запрос к поисковому API и возвращает топ URL."""
    encoded_query = query.replace("&", "%26")
    params_with_auth = params.copy()
    params_with_auth.update({"user": USER, "key": API_KEY, "query": encoded_query})

    logger.info(
        f"Отправка запроса к API для '{query}' с параметрами: {params_with_auth}"
    )

    # Логирование итогового URL
    final_url = requests.Request("GET", base_url, params=params_with_auth).prepare().url
    logger.info(f"Итоговый URL для запроса: {final_url}")

    for attempt in range(RETRY_ATTEMPTS):
        try:
            logger.info(f"Попытка {attempt + 1} для запроса '{query}'")
            response = requests.get(base_url, params=params_with_auth, timeout=120)
            response.raise_for_status()

            response_text = response.text
            logger.info(
                f"HTTP статус: {response.status_code}, Первые 500 символов ответа: {response_text[:500]}"
            )

            urls = get_top_urls_from_response(response_text, depth)
            return urls

        except Exception as e:
            logger.error(f"Ошибка для запроса '{query}' (попытка {attempt + 1}): {e}")
            if attempt < RETRY_ATTEMPTS - 1:
                logger.info(
                    f"Ожидание {RETRY_DELAY} секунд перед повторной попыткой..."
                )
                sleep(RETRY_DELAY)
            continue

    logger.warning(
        f"Не удалось обработать запрос '{query}' после {RETRY_ATTEMPTS} попыток"
    )
    return []


def make_live_search_request(query, base_url, params, depth, page_num):
    """Выполняет один запрос к 'живому поиску' для конкретной страницы."""

    # Определяем номер страницы в зависимости от поисковой системы
    if "yandex" in base_url:
        # Для Яндекса страницы начинаются с 0
        page_to_request = page_num
    else:
        # Для Google страницы начинаются с 1
        page_to_request = page_num + 1

    logger.info(
        f"Запуск 'Живого поиска' для страницы {page_to_request} для запроса '{query}'"
    )

    current_params = params.copy()
    current_params["page"] = page_to_request

    # Запрашиваем 10 результатов, так как это одна страница
    page_urls = make_search_request(query, base_url, current_params, 10)

    return page_urls


def parse_top_sites(
    query,
    search_engine,
    region,
    device,
    depth,
    yandex_type="search_api",
    page_num=0,
    loc_id=20949,
):
    """
    Выполняет парсинг "живой" поисковой выдачи (только органические результаты) для одной страницы.

    :param query: поисковый запрос
    :param search_engine: поисковая система
    :param region: регион поиска
    :param device: тип устройства
    :param depth: глубина парсинга (для Google и Yandex Search API)
    :param yandex_type: тип поиска Яндекса (search_api или live_search)
    :param page_num: номер страницы для 'live_search'
    :return: список URL-адресов
    """
    logger.info(
        f"Начало парсинга ТОП-сайтов для запроса: '{query}', поисковик: {search_engine}, страница: {page_num}"
    )

    # Настройка региона в зависимости от поисковой системы
    if search_engine == "google":
        lr = "RU"
        domain_id = 10

        BASE_URL = "http://xmlriver.com/search/xml"
        params = {
            "loc": loc_id,
            "lr": lr,
            "domain": domain_id,
            "device": device or "desktop",
            "groupby": 10,  # для "Живого поиска" обычно 10 результатов на страницу
        }

        # Для Google используем постраничный поиск
        urls = make_live_search_request(query, BASE_URL, params, depth, page_num)
        return urls
    else:  # yandex
        # Используем параметры региона для Яндекс
        # Значения по умолчанию
        lr_id = 213  # Москва
        lang = "ru"
        domain = "ru"

        # Маппинг регионов для Яндекса
        if region == "RU":
            lr_id = 213  # Москва
            lang = "ru"
            domain = "ru"
        elif region == "UA":
            lr_id = 223  # Киев
            lang = "uk"
            domain = "ua"
        elif isinstance(region, int) or (isinstance(region, str) and region.isdigit()):
            # Если в region передан числовой ID
            lr_id = int(region)
            logger.info(f"Использование числового ID региона из 'region': {lr_id}")
        elif isinstance(loc_id, int) or (
            isinstance(loc_id, str) and str(loc_id).isdigit()
        ):
            # Если в loc_id передан числовой ID и он не равен дефолту Google (20949)
            if int(loc_id) != 20949:
                lr_id = int(loc_id)
                logger.info(f"Использование числового ID региона из 'loc_id': {lr_id}")
        # Можно добавить другие регионы при необходимости

        # Для Яндекса определяем, использовать ли живой поиск или search API
        # Используем переданный yandex_type
        if yandex_type == "live_search":
            # Живой поиск - делаем несколько запросов для получения нужной глубины
            BASE_URL = "http://xmlriver.com/search_yandex/xml"
            params = {
                "lr": lr_id,
                "lang": lang,
                "domain": domain,
                "device": device or "desktop",
                "groupby": 10,  # для "Живого поиска" обычно 10 результатов на страницу
            }
            # Вызываем живой поиск для конкретной страницы
            urls = make_live_search_request(query, BASE_URL, params, depth, page_num)
            return urls
        else:  # search_api (по умолчанию)
            # Search API - один запрос с указанной глубиной
            BASE_URL = "http://xmlriver.com/yandex/xml"
            params = {
                "lr": lr_id,
                "lang": lang,
                "domain": domain,
                "device": device or "desktop",
                "groupby": 100,  # для Search API всегда запрашиваем 100, так как стоимость одного запроса фиксированная
            }
            urls = make_search_request(query, BASE_URL, params, depth * 10)
            return urls
