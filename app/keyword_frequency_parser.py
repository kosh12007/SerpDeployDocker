# -*- coding: utf-8 -*-
"""
Модуль для парсинга частотности ключевых слов с использованием API XMLRiver (Wordstat).

Поддерживаемые функции:
- Получение базовой частотности для Яндекса
- Получение фразовой частотности для Яндекса
- Получение точной частотности для Яндекса
- Заглушка для частотности Google (не поддерживается API XMLRiver)
"""

import os
import requests
import logging
import json  # Используем json вместо xmltodict
import re
from time import sleep
from typing import Optional, Dict
from urllib.parse import urlparse, parse_qs
from enum import Enum
from app.db_config import LOGGING_ENABLED

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "keyword_frequency_parser.log")
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


from enum import Enum


class FrequencyType(Enum):
    """
    Тип частотности ключевого слова.
    """

    YANDEX_BASIC = "yandex_basic"
    YANDEX_PHRASE = "yandex_phrase"
    YANDEX_EXACT = "yandex_exact"
    GOOGLE_BASIC = "google_basic"
    GOOGLE_REFINED = "google_refined"


def _construct_yandex_query(keyword: str, freq_type: str) -> str:
    """
    Конструирует строку запроса для Яндекса в зависимости от типа частотности.

    :param keyword: Исходное ключевое слово.
    :param freq_type: Тип частотности (строка).
    :return: Строка запроса для API Яндекса.
    """
    if freq_type == FrequencyType.YANDEX_BASIC.value:
        # Базовая частотность: просто передаем ключевое слово
        return keyword
    elif freq_type == FrequencyType.YANDEX_PHRASE.value:
        # Фразовая частотность: заключаем в двойные кавычки
        return f'"{keyword}"'
    elif freq_type == FrequencyType.YANDEX_EXACT.value:
        # Точная частотность: добавляем восклицательный знак перед каждым словом, но без внешних кавычек
        words = keyword.split()
        quoted_words = [f"!{word}" for word in words]
        return f'{" ".join(quoted_words)}'
    else:
        # Для других типов возвращаем исходное слово
        return keyword


def get_frequency(
    query,
    user,
    key,
    base_url,
    freq_type,
    region_id=None,
    retry_attempts=3,
    retry_delay=5,
):
    """
    Получает частотность ключевого слова для Яндекс Wordstat.

    Args:
        query: Ключевое слово для анализа
        user: Пользователь XmlRiver API
        key: Ключ XmlRiver API
        base_url: Базовый URL API (http://xmlriver.com/wordstat/new/json)
        freq_type: Тип частотности ('yandex_basic', 'yandex_phrase', 'yandex_exact')
        region_id: Идентификатор региона Яндекса (необязательный)
        retry_attempts: Количество попыток при ошибке
        retry_delay: Задержка между попытками в секундах

    Returns:
        tuple: (frequency, success)
            - frequency: Частотность (количество запросов в месяц) или None если не найдено или ошибка
            - success: True если запрос успешен, False если ошибка
    """
    yandex_query = _construct_yandex_query(query, freq_type)
    safe_query = re.sub(r"[^\w\s-]", "", query.lower()).replace(" ", "_")

    logger.info(
        f"Начало получения частотности для запроса: '{query}', тип: {freq_type}, регион: {region_id}"
    )
    logger.info(f"Форматированный запрос для API: '{yandex_query}' (тип: {freq_type})")

    # Подготовка параметров
    params = {
        "user": user,
        "key": key,
        "query": yandex_query,
        "pagetype": "history",  # Используем 'history' для получения TotalValue
    }

    # Для эндпоинта wordstat/new/json различие между типами частотности
    # определяется форматом самого запроса (yandex_query), а не специальным параметром
    # yandex_query уже модифицирован в _construct_yandex_query в зависимости от типа частотности

    if region_id:
        params["regions"] = region_id

    # Логируем полную ссылку запроса
    full_url = requests.Request("GET", base_url, params=params).prepare().url
    if LOGGING_ENABLED:
        logger.info(f"Полная ссылка запроса: {full_url}")
        logger.info(f"Параметры запроса: {params}")

    for attempt in range(retry_attempts):
        try:
            if LOGGING_ENABLED:
                logger.info(
                    f"Попытка {attempt + 1} для запроса '{query}' (тип: {freq_type})"
                )

            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()

            response_text = response.text

            if LOGGING_ENABLED:
                logger.info(
                    f"HTTP статус: {response.status_code}, Полный ответ API: {response_text}"
                )

            # Попытка парсинга JSON
            try:
                if LOGGING_ENABLED:
                    logger.debug(
                        f"Попытка парсинга JSON для запроса '{query}' (тип: {freq_type})"
                    )

                data = response.json()

                if LOGGING_ENABLED:
                    logger.info(
                        f"JSON структура (ключи верхнего уровня): {list(data.keys())}"
                    )

                if "error" in data:
                    error_code = data["error"].get("@code", "unknown")
                    if error_code == "15":
                        if LOGGING_ENABLED:
                            logger.info(
                                f"Запрос '{query}' (тип: {freq_type}): Нет результатов (код 15)"
                            )
                        return None, True  # Успешно, но частотность 0 или не найдена
                    else:
                        raise Exception(f"API ошибка: код {error_code}")

                # Структура ответа для wordstat/new/json может отличаться.
                # Из логов видно, что частотность может быть в поле 'totalValue' верхнего уровня.
                # Пример структуры: {"...": {...}, "totalValue": "139"}

                total_value_raw = data.get("totalValue")

                if total_value_raw is not None:
                    try:
                        frequency_int = int(total_value_raw)
                        if LOGGING_ENABLED:
                            logger.info(
                                f"Частотность (totalValue) для '{yandex_query}' (тип: {freq_type}): {frequency_int}"
                            )
                        return frequency_int, True
                    except ValueError:
                        logger.warning(
                            f"Значение частотности (totalValue) не является числом: {total_value_raw} (запрос: {yandex_query}, тип: {freq_type})"
                        )
                        return None, True  # Успешный ответ, но частотность не числовая
                else:
                    # Если totalValue на верхнем уровне нет, пробуем найти absoluteValue в graph.tableData[0]
                    graph_data = data.get("graph")
                    if graph_data:
                        table_data_list = graph_data.get("tableData")
                        if (
                            table_data_list
                            and isinstance(table_data_list, list)
                            and len(table_data_list) > 0
                        ):
                            first_table_entry = table_data_list[0]
                            abs_val = first_table_entry.get("absoluteValue")
                            if abs_val:
                                try:
                                    freq_from_graph = int(abs_val)
                                    if LOGGING_ENABLED:
                                        logger.info(
                                            f"Частотность (из graph.tableData) для '{yandex_query}' (тип: {freq_type}): {freq_from_graph}"
                                        )
                                    return freq_from_graph, True
                                except ValueError:
                                    logger.warning(
                                        f"Значение absoluteValue из graph.tableData не является числом: {abs_val}"
                                    )
                                    return (
                                        None,
                                        True,
                                    )  # Успешный ответ, но частотность не числовая
                    logger.warning(
                        f"Поля 'totalValue' или 'graph.tableData[0].absoluteValue' отсутствуют в ответе API для '{yandex_query}' (тип: {freq_type}). Ответ: {data}"
                    )
                    # Успешный ответ, но частотность не найдена в ожидаемых полях
                    return None, True

            except json.JSONDecodeError as json_e:
                if LOGGING_ENABLED:
                    logger.error(
                        f"Ошибка парсинга JSON для '{query}' (тип: {freq_type}): {json_e}. Ответ: {response_text[:200]}..."
                    )
                return None, False  # Ошибка парсинга JSON
            except Exception as e:
                if LOGGING_ENABLED:
                    logger.error(
                        f"Неожиданная ошибка при парсинге ответа для '{query}' (тип: {freq_type}): {e}",
                        exc_info=True,
                    )
                return None, False  # Ошибка парсинга

        except requests.exceptions.RequestException as req_e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка запроса к API для '{query}' (тип: {freq_type}) (попытка {attempt + 1}): {req_e}"
                )
        except Exception as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Неожиданная ошибка для запроса '{query}' (тип: {freq_type}) (попытка {attempt + 1}): {e}",
                    exc_info=True,
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
            f"Не удалось получить частотность для '{query}' (тип: {freq_type}) после {retry_attempts} попыток"
        )
    return None, False


def get_frequency_single_query(query, freq_type, region_id=None):
    """
    Получает частотность для одного ключевого слова (совместимость со старым кодом).

    Args:
        query: Ключевое слово для анализа
        freq_type: Тип частотности
        region_id: Идентификатор региона Яндекса (необязательный)

    Returns:
        int or None: Частотность или None в случае ошибки или отсутствия данных
    """
    user, key = get_api_credentials()
    if not user or not key:
        logger.error("Не удалось получить учетные данные API")
        return None

    base_url = (
        "http://xmlriver.com/wordstat/new/json"  # Используем указанный базовый URL
    )

    frequency, success = get_frequency(query, user, key, base_url, freq_type, region_id)

    if not success:
        logger.error(
            f"Ошибка при получении частотности для '{query}' (тип: {freq_type})"
        )
        return None

    return frequency  # Возвращаем только частотность, как в старом варианте


class KeywordFrequencyParser:
    """
    Класс для парсинга частотности ключевых слов (совместимость со старым интерфейсом).
    Использует новые функции для выполнения запросов к API.
    """

    def __init__(self):
        """
        Инициализирует парсер частотности, извлекая учетные данные из переменной окружения.
        """
        self.api_user_id, self.api_key = get_api_credentials()
        if not self.api_user_id or not self.api_key:
            raise ValueError(
                "Не удалось получить учетные данные API из переменной окружения API_KEY."
            )

        # URL для получения данных о частотности Яндекса (Wordstat)
        self.base_wordstat_url = "http://xmlriver.com/wordstat/new/json"

    def get_frequency(
        self, keyword: str, freq_type: FrequencyType, region_id: Optional[str] = None
    ) -> Optional[int]:
        """
        Получает частотность ключевого слова для указанного типа (новая реализация).

        :param keyword: Ключевое слово для анализа.
        :param freq_type: Тип частотности (YANDEX_BASIC, YANDEX_PHRASE, YANDEX_EXACT).
        :param region_id: Идентификатор региона Яндекса (необязательный).
        :return: Частотность (количество запросов в месяц) или None в случае ошибки или отсутствия данных.
        """
        if freq_type in [
            FrequencyType.YANDEX_BASIC,
            FrequencyType.YANDEX_PHRASE,
            FrequencyType.YANDEX_EXACT,
        ]:
            # Передаем оригинальное ключевое слово, а не уже отформатированное
            logger.info(
                f"Выполняется запрос к API Яндекса для получения частотности. Тип: {freq_type.value}, Запрос: {keyword}, Регион: {region_id}"
            )

            frequency, success = get_frequency(
                keyword,  # передаем оригинальное слово, а не отформатированное
                self.api_user_id,
                self.api_key,
                self.base_wordstat_url,
                freq_type.value,  # передаем .value, так как get_frequency ожидает строку
                region_id=region_id,
            )

            if success:
                return frequency
            else:
                logger.error(
                    f"Не удалось получить частотность для '{keyword}' (тип: {freq_type.value})"
                )
                return None

        elif freq_type in [FrequencyType.GOOGLE_BASIC, FrequencyType.GOOGLE_REFINED]:
            # API XMLRiver не предоставляет данных о частотности запросов в Google
            logger.warning(
                f"Получение частотности для Google ({freq_type.value}) не поддерживается API XMLRiver."
            )
            return None

        else:
            logger.error(f"Неподдерживаемый тип частотности: {freq_type.value}")
            return None
