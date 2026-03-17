#!/var/www/u0669189/data/serp/bin/python
# -*- coding: utf-8 -*-

import pandas as pd
import requests
import xmltodict
import os
from time import sleep
from dotenv import load_dotenv
import logging
from urllib.parse import urlparse, parse_qs
import sys
import io
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import mysql.connector
from mysql.connector import Error
from flask import Flask, request, render_template, redirect, url_for, session, jsonify

# from top_sites_parser import parse_top_sites

# Счетчик использованных лимитов (потокобезопасный)
used_limits = 0
used_limits_lock = threading.Lock()
from datetime import datetime
from collections import Counter
from app.xmlriver_client import (
    get_live_search_position_looped,
    get_google_position_looped,
    get_position_and_url_single_page,
)

# Исправляем кодировку консоли для Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    os.system("chcp 65001 > nul")
    try:
        import subprocess

        subprocess.run(
            [
                "powershell",
                "-Command",
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8",
            ],
            capture_output=True,
        )
    except:
        pass

# --- Настройка логгера ---
# Создаем папку logs, если она не существует
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

# Настраиваем логгер для текущего модуля
log_file = os.path.join(log_dir, "main_script.log")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False  # Отключаем передачу логов вышестоящим логгерам (консоли)

# Предотвращаем двойное логирование, если обработчик уже есть
if not logger.handlers:
    # Создаем обработчик для записи в файл
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # Создаем форматтер
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Добавляем обработчик к логгеру
    logger.addHandler(file_handler)

logger.info(f"Логгер для {__name__} настроен.")
# --- Конец настройки логгера ---

# Загрузка настроек из .env
load_dotenv()

# Настройки с fallback значениями
API_URL = os.getenv("API_KEY")
INPUT_FILE = os.getenv("INPUT_FILE", "queries.xlsx")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "results.xlsx")
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", 3))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", 10))

# Настройки базы данных
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "u0669189_serp"),
    "user": os.getenv("DB_USER", "u0669189_serp"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 3306)),
}


def create_db_connection():
    """Создает подключение к базе данных MySQL"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        logger.error(f"Ошибка подключения к MySQL: {e}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка подключения к MySQL: {e}")
        return None


def save_results_to_db(results, session_id):
    """Сохраняет результаты парсинга в базу данных в оригинальные таблицы (parsing_sessions, parsing_results, session_results)"""
    try:
        logger.info(
            f"Начало сохранения результатов в базу данных для сессии {session_id}, количество результатов: {len(results)}"
        )

        connection = create_db_connection()
        if connection:
            cursor = connection.cursor()

            # Для старого функционала user_id не используется, так как данные сохраняются в таблицу parsing_results без привязки к пользователю напрямую
            # Вместо этого используется session_id для привязки результатов к сессии через таблицу session_results
            user_id = None  # Устанавливаем в None для старого функционала
            logger.info(
                f"Для старого функционала user_id установлен в None, используем session_id: {session_id}"
            )

            # Вставляем новые результаты в оригинальную таблицу parsing_results
            insert_query = """
            INSERT INTO parsing_results (query, position, url, processed)
            VALUES (%s, %s, %s, %s)
            """
            # Пропускаем user_id, так как для старого функционала он не нужен
            # Вместо этого используем только необходимые поля

            result_ids = []
            for i, result in enumerate(results):
                # Проверяем, что результат содержит необходимые поля
                query = result.get("Запрос", result.get("Query", ""))
                position = result.get("Позиция", result.get("Position", None))
                url = result.get("URL", result.get("url", ""))
                status = result.get("Статус", result.get("Processed", ""))

                # Логируем значения перед сохранением для отладки
                logger.debug(
                    f"Сохранение результата {i+1}/{len(results)}: запрос='{query}', позиция='{position}', URL='{url}'"
                )

                # Обрабатываем позицию: если это '-', преобразуем в None для сохранения как NULL в базе
                if position is None or position == "-" or position == "":
                    position = None
                elif isinstance(position, str) and position.isdigit():
                    position = int(position)
                elif isinstance(position, str) and position.lstrip("-").isdigit():
                    position = int(position)
                else:
                    try:
                        position = int(position)
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Позиция '{position}' не является числом, устанавливаем в None"
                        )
                        position = None

                # Обрабатываем URL: если это '-' или пустая строка, сохраняем как '-' в базу
                # Согласно примеру, когда домен не найден, URL должен быть '-'
                if url is None or url == "" or url == "-":
                    url = "-"

                cursor.execute(insert_query, (query, position, url, status))
                # Получаем ID вставленной записи
                result_id = cursor.lastrowid
                result_ids.append(result_id)
                logger.debug(f"Вставлен результат с ID: {result_id}")

            # Привязываем результаты к сессии в оригинальной таблице session_results
            logger.info(
                f"ID результатов для привязки к сессии {session_id}: {result_ids}"
            )
            if result_ids:
                session_result_query = """
                INSERT INTO session_results (session_id, result_id)
                VALUES (%s, %s)
                """
                for result_id in result_ids:
                    cursor.execute(session_result_query, (session_id, result_id))
                    logger.debug(
                        f"Привязан результат {result_id} к сессии {session_id}"
                    )

            connection.commit()
            cursor.close()
            connection.close()

            logger.info(
                f"Результаты успешно сохранены в базу данных для сессии {session_id}, всего сохранено: {len(results)}"
            )
        else:
            logger.error(
                f"Не удалось создать подключение к базе данных для сессии {session_id}"
            )
    except Error as e:
        logger.error(
            f"Ошибка сохранения результатов в базу данных для сессии {session_id}: {e}"
        )


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_default_secret_key")

# Извлечение user и key из API_URL
try:
    parsed_url = urlparse(API_URL)
    query_params = parse_qs(parsed_url.query)
    USER = query_params.get("user", [None])[0]
    API_KEY = query_params.get("key", [None])[0]
    if not USER or not API_KEY:
        raise ValueError("Не удалось извлечь user или key из API_URL")
except Exception as e:
    logger.error(f"Ошибка парсинга API_URL: {e}")
    print(f"Ошибка: Некорректный API_URL в .env: {e}")
    exit(1)


def get_domain_from_url(url_str):
    """Извлекает чистый домен из URL."""
    if not url_str:
        return ""
    parsed = urlparse(url_str.lower())
    return parsed.netloc.replace("www.", "").rstrip("/")


def parse_text_serp(text, site_url, safe_query):
    """Fallback: Парсит только URL из тегов <url> в XML, сохраняя порядок групп."""
    logger.info(f"Запуск fallback парсинга текста для сайта: {site_url}")
    urls = re.findall(r"<url>(https?://[^<]+)</url>", text)
    site_domain = get_domain_from_url(site_url)
    logger.info(
        f"Fallback: Найдено {len(urls)} URL в тегах <url> для поиска домена '{site_domain}'"
    )

    # Сохраняем все URL для отладки — отдельный файл для каждого запроса
    # filename = f"all_urls_{site_domain}_{safe_query}.xml"
    # with open(filename, "w", encoding="utf-8") as f:
    #     for i, url in enumerate(urls, 1):
    #         f.write(f"Позиция {i}: {url}\n")
    # logger.info(f"Все URL сохранены в {filename} (до {len(urls)})")

    position = None
    found_url = None
    for i, url in enumerate(urls, 1):
        doc_domain = get_domain_from_url(url)
        logger.debug(f"Позиция {i}: URL '{url}' (домен '{doc_domain}')")
        if site_domain in doc_domain or doc_domain in site_domain:
            position = i
            found_url = url
            logger.info(f"Fallback: Найден домен на позиции {i}: {url}")
            break
    logger.info(f"Fallback завершен: позиция={position}, URL={found_url}")
    return position, found_url


def process_single_query(
    query,
    index,
    total_queries,
    engine,
    yandex_type,
    BASE_URL,
    base_params,
    site_url,
    yandex_page_limit,
    google_page_limit,
):
    """
    Обрабатывает один поисковый запрос к XMLRiver API.
    Функция вынесена для использования в ThreadPoolExecutor.

    Args:
        query: Поисковый запрос
        index: Номер запроса (для логирования)
        total_queries: Общее количество запросов
        engine: Поисковая система
        yandex_type: Тип поиска Яндекса
        BASE_URL: Базовый URL API
        base_params: Базовые параметры запроса (будет скопирован)
        site_url: URL сайта для поиска
        yandex_page_limit: Лимит страниц для Яндекса
        google_page_limit: Лимит страниц для Google

    Returns:
        dict: Результат обработки запроса
    """
    query = str(query).strip()
    if not query:
        logger.warning(f"Пропуск пустого запроса на позиции {index}")
        return None

    logger.info(f"Обработка [{index}/{total_queries}]: {query}")

    # Создаём копию параметров для каждого потока (избегаем race condition)
    thread_params = base_params.copy()
    thread_params.update(
        {"user": USER, "key": API_KEY, "query": query.replace("&", "%26")}
    )

    logger.info(
        f"[{index}/{total_queries}] Формирование запроса к XMLRiver. BASE_URL: {BASE_URL}"
    )
    logger.info(
        f"[{index}/{total_queries}] Параметры запроса (без ключа): { {k:v for k,v in thread_params.items() if k!='key'} }"
    )

    logger.debug(f"Отправка запроса к API для '{query}' с параметрами: {thread_params}")

    if engine == "yandex" and yandex_type == "live_search":
        position, url, success = get_live_search_position_looped(
            query, USER, API_KEY, BASE_URL, thread_params, site_url, yandex_page_limit
        )
    elif engine == "google":
        position, url, success = get_google_position_looped(
            query, USER, API_KEY, BASE_URL, thread_params, site_url, google_page_limit
        )
    else:  # yandex search_api
        # Для 'search_api' вызываем одностраничный парсер
        position, url, success = get_position_and_url_single_page(
            query, USER, API_KEY, BASE_URL, engine, thread_params, site_url
        )

    logger.debug(
        f"Получен результат для '{query}': position={position}, url={url}, success={success}"
    )

    result = {
        "Запрос": query,
        "Позиция": position if position else "-",
        "URL": url if url else "-",
        "Статус": "Yes" if success else "No",
        "_index": index,  # Сохраняем порядок для сортировки результатов
    }
    logger.debug(f"Результат для запроса [{index}]: {result}")
    return result


def main(
    engine="google",
    queries_file=None,
    domain=None,
    output_file=None,
    yandex_type="search_api",
    yandex_page_limit=9,
    google_page_limit=10,
    loc_id=213,
    threads=5,
):
    """Основная функция с параметром поисковика и многопоточностью"""

    logger.info(f"=== НАЧАЛО main.py ===")
    logger.info(f"Глобальные USER/API_KEY: {USER}/{API_KEY[:5]}***")
    logger.info(f"Выбран поисковик: {engine}, тип Яндекса: {yandex_type}")
    logger.info(
        f"Запуск с поисковиком: {engine}, тип Яндекса: {yandex_type}, лимит страниц Yandex: {yandex_page_limit}, лимит страниц Google: {google_page_limit}, потоков: {threads}"
    )
    logger.info(
        f"Параметры: engine={engine}, queries_file={queries_file}, domain={domain}, output_file={output_file}, yandex_type={yandex_type}, yandex_page_limit={yandex_page_limit}, google_page_limit={google_page_limit}, loc_id={loc_id}, threads={threads}"
    )

    # Настройки для поисковика
    if engine == "google":
        BASE_URL = "http://xmlriver.com/search/xml"
        params = {
            "loc": loc_id,  # Регион для Google
            "country": 2008,  # RU
            "lr": "RU",
            "domain": 10,  # Google .com
            "device": "desktop",
            "groupby": 10,
        }
    else:  # yandex
        if yandex_type == "live_search":
            BASE_URL = "http://xmlriver.com/search_yandex/xml"
            params = {
                "lr": loc_id,  # Регион для Yandex
                "lang": "ru",
                "domain": "ru",
                "device": "desktop",
                "groupby": 10,  # для "Живого поиска"
            }
        else:  # search_api (по умолчанию)
            BASE_URL = "http://xmlriver.com/yandex/xml"
            params = {
                "lr": loc_id,  # Регион для Yandex
                "lang": "ru",
                "domain": "ru",
                "device": "desktop",
                "groupby": 100,  # для Search API
            }

    # Проверки
    if not USER or not API_KEY:
        print("Ошибка: Не удалось извлечь USER или API_KEY из .env.")
        logger.error("USER или API_KEY отсутствуют")
        return

    # Если переданы параметры из веб-интерфейса, используем их
    if queries_file and domain:
        try:
            logger.info(f"Начало чтения поисковых фраз из файла: {queries_file}")
            logger.info(f"Чтение поисковых фраз из файла: {queries_file}")
            with open(queries_file, "r", encoding="utf-8") as f:
                queries = [line.strip() for line in f.readlines() if line.strip()]

            site_url = domain.strip()

            if not site_url:
                raise ValueError("Домен не указан.")

            if not queries:
                raise ValueError("Нет поисковых фраз для обработки.")

            logger.info(f"Домен: {site_url} (ENGINE: {engine})")
            logger.info(f"Домен: {site_url} (ENGINE: {engine})")
            logger.info(f"Найдено поисковых фраз: {len(queries)}")
            logger.info(f"Найдено поисковых фраз: {len(queries)}")
            logger.info(f"Список поисковых фраз: {queries}")

        except Exception as e:
            print(f"Ошибка чтения временного файла: {e}")
            logger.error(f"Чтение временного файла: {e}")
            return
    else:
        # Используем старую логику с Excel-файлом
        if not os.path.exists(INPUT_FILE):
            print(f"Ошибка: Файл {INPUT_FILE} не найден!")
            logger.error(f"Файл {INPUT_FILE} не найден")
            return

        try:
            df = pd.read_excel(INPUT_FILE, header=None, engine="openpyxl")
            if df.empty or df.shape[1] < 1:
                raise ValueError("Файл пустой.")

            site_url = str(df.iloc[0, 0]).strip()  # Домен из A1
            if not site_url:
                raise ValueError("A1 пуста — укажите домен.")

            logger.info(f"Домен: {site_url} (ENGINE: {engine})")
            logger.info(f"Домен: {site_url} (ENGINE: {engine})")

            queries = df.iloc[1:, 0].dropna().tolist()

            if not queries:
                raise ValueError("Нет запросов в столбце A.")

            logger.info(f"Найдено запросов в столбце A: {len(queries)}")
            logger.info(f"Найдено запросов в столбце A: {len(queries)}")

        except Exception as e:
            print(f"Ошибка чтения {INPUT_FILE}: {e}")
            logger.error(f"Чтение файла: {e}")
            return

    # Обработка запросов в многопоточном режиме
    results = []
    total_queries = len(queries)

    # Ограничиваем количество потоков количеством запросов
    actual_threads = min(threads, total_queries)
    logger.info(
        f"Начинаем многопоточную обработку {total_queries} запросов в {actual_threads} потоках"
    )
    logger.info(f"Начинаем обработку {total_queries} запросов")

    with ThreadPoolExecutor(max_workers=actual_threads) as executor:
        # Создаём словарь {future: (query, index)} для отслеживания
        future_to_query = {}
        for index, query in enumerate(queries, 1):
            future = executor.submit(
                process_single_query,
                query=query,
                index=index,
                total_queries=total_queries,
                engine=engine,
                yandex_type=yandex_type,
                BASE_URL=BASE_URL,
                base_params=params,
                site_url=site_url,
                yandex_page_limit=yandex_page_limit,
                google_page_limit=google_page_limit,
            )
            future_to_query[future] = (query, index)

        # Собираем результаты по мере завершения потоков
        for future in as_completed(future_to_query):
            query, index = future_to_query[future]
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
                    logger.debug(
                        f"Получен результат потока [{index}/{total_queries}] для '{query}'"
                    )
            except Exception as exc:
                logger.error(
                    f"Поток для запроса '{query}' [{index}] завершился с ошибкой: {exc}"
                )
                results.append(
                    {
                        "Запрос": str(query).strip(),
                        "Позиция": "-",
                        "URL": "-",
                        "Статус": "No",
                        "_index": index,
                    }
                )

    # Сортируем результаты по исходному порядку запросов
    results.sort(key=lambda r: r.get("_index", 0))
    # Удаляем служебное поле _index из результатов
    for r in results:
        r.pop("_index", None)

    logger.info(
        f"Многопоточная обработка завершена. Получено {len(results)} результатов из {total_queries} запросов"
    )

    # Сохранение
    try:
        result_df = pd.DataFrame(results)

        successful = [
            r
            for r in results
            if r["Статус"] == "Yes" and r["Позиция"] != "-" and r["Позиция"] is not None
        ]
        positions = [
            int(r["Позиция"])
            for r in successful
            if isinstance(r["Позиция"], (int, str)) and r["Позиция"] != "-"
        ]

        if positions:
            avg_position = sum(positions) / len(positions)
            top_10 = len([p for p in positions if p <= 10])

        session_id = os.environ.get("SESSION_ID")
        if session_id:
            logger.info(f"Обнаружен session_id: {session_id} из переменных окружения")
            save_results_to_db(results, session_id)

            # Обновляем статус сессии и потраченные лимиты
            # try:
            #     update_position_session_status(session_id, 'completed')
            #     update_position_session_spent_limits(session_id, used_limits)
            #     logger.info(f"Статус сессии {session_id} обновлен на 'completed' и списано {used_limits} лимитов.")
            # except Exception as update_e:
            #     logger.error(f"Ошибка при обновлении статуса или лимитов для сессии {session_id}: {update_e}", exc_info=True)

        else:
            logger.info("session_id не найден в переменных окружения")
            logger.warning(
                "Результаты не будут сохранены в базу данных, так как отсутствует session_id"
            )

        # Выводим количество использованных лимитов
        logger.info(f"=== ИТОГО ИСПОЛЬЗОВАНО ЛИМИТОВ: {used_limits} ===")

    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        logger.error(f"Сохранение: {e}")
        session_id = os.environ.get("SESSION_ID")
        if session_id:
            try:
                # В случае ошибки парсинга, помечаем сессию как 'error'
                # Используем функцию из app.db.database для обновления статуса старой системы сессий
                from app.db.database import update_session_status

                update_session_status(session_id, "error")
                logger.info(
                    f"Статус сессии {session_id} обновлен на 'error' из-за ошибки."
                )
            except Exception as final_update_e:
                logger.error(
                    f"Критическая ошибка: не удалось обновить статус сессии {session_id} на 'error': {final_update_e}",
                    exc_info=True,
                )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Парсер поисковой выдачи.")
    parser.add_argument(
        "engine",
        nargs="?",
        default="google",
        help="Поисковая система (google или yandex)",
    )
    parser.add_argument(
        "queries_file", nargs="?", default=None, help="Файл с поисковыми запросами"
    )
    parser.add_argument("domain", nargs="?", default=None, help="Домен для поиска")
    parser.add_argument(
        "yandex_type",
        nargs="?",
        default="search_api",
        help="Тип поиска Яндекса (search_api или live_search)",
    )
    parser.add_argument(
        "yandex_page_limit",
        nargs="?",
        type=int,
        default=9,
        help="Глубина проверки для 'Живого поиска' Яндекса",
    )
    parser.add_argument(
        "google_page_limit",
        nargs="?",
        type=int,
        default=10,
        help="Глубина проверки для Google",
    )
    parser.add_argument(
        "loc_id",
        nargs="?",
        type=int,
        default=213,
        help="ID региона (lr для Yandex, loc для Google)",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=5,
        help="Количество потоков для параллельной обработки запросов",
    )

    args = parser.parse_args()

    main(
        engine=args.engine,
        queries_file=args.queries_file,
        domain=args.domain,
        output_file=None,  # output_file больше не используется напрямую
        yandex_type=args.yandex_type,
        yandex_page_limit=args.yandex_page_limit,
        google_page_limit=args.google_page_limit,
        loc_id=args.loc_id,
        threads=args.threads,
    )
