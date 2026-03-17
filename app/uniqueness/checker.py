import re
import os
import logging
from typing import List, Dict, Optional, Tuple, Set
import requests
import xmltodict
import time
import uuid
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.xmlriver_client import get_api_credentials
from app.db_config import LOGGING_ENABLED

# LOGGING_ENABLED = True  # True для включения логгирования, или закомментировать чтобы получать глобальные настройки из from app.db_config import LOGGING_ENABLED
logger = logging.getLogger(__name__)

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "uniqueness_checker.log")
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

# Попытка инициализации NLTK
try:
    import nltk
    from nltk.corpus import stopwords

    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords", quiet=True)

    STOPWORDS: Set[str] = set(stopwords.words("russian"))
    from nltk.stem.snowball import SnowballStemmer

    STEMMER = SnowballStemmer("russian")
except Exception as e:
    logger.warning(
        f"NLTK stopwords недоступны: {e}. Используется пустой список стоп-слов."
    )
    STOPWORDS = set()
    STEMMER = None

# Исправление совместимости pymorphy2 с Python 3.11+ (monkeypatching inspect.getargspec)
import inspect

if not hasattr(inspect, "getargspec"):

    def getargspec(func):
        full = inspect.getfullargspec(func)
        return (full.args, full.varargs, full.varkw, full.defaults)

    inspect.getargspec = getargspec

# Попытка инициализации pymorphy2
try:
    import pymorphy2

    morph = pymorphy2.MorphAnalyzer()
except ImportError:
    logger.info(
        "pymorphy2 не установлен. Будет использоваться NLTK Stemmer (стемминг)."
    )
    morph = None


class UniquenessChecker:
    """
    Класс для проверки уникальности текста через поисковую выдачу XMLRiver.
    """

    def __init__(self):
        self.user, self.key = get_api_credentials()
        # Изменяем базовый URL на корректный для Яндекс XML от XMLRiver
        self.base_url = "http://xmlriver.com/yandex/xml"
        if not self.user or not self.key:
            logger.error(
                "XMLRiver credentials не найдены. Проверка уникальности не будет работать."
            )

    def preprocess_text(self, text: str) -> List[str]:
        """
        Предварительная обработка текста:
        - Приведение к нижнему регистру
        - Удаление пунктуации
        - Удаление стоп-слов
        - Лемматизация (если доступен pymorphy2)

        Args:
            text (str): Исходный текст.

        Returns:
            List[str]: Список обработанных слов.
        """
        # 1. Нижний регистр
        text = text.lower()

        # 2. Удаление пунктуации (оставляем буквы, цифры и пробелы)
        text = re.sub(r"[^\w\s]", "", text)

        # 3. Разбиение на слова
        words = text.split()

        # 4. Фильтрация и лемматизация
        clean_words = []
        for word in words:
            # Пропускаем стоп-слова и слишком короткие слова
            if word not in STOPWORDS and len(word) > 2:
                if morph:
                    p = morph.parse(word)[0]
                    clean_words.append(p.normal_form)
                elif STEMMER:
                    clean_words.append(STEMMER.stem(word))
                else:
                    clean_words.append(word)

        return clean_words

    def get_shingles(self, text: str, n: int = 4) -> List[Dict]:
        """
        Разбиение текста на шинглы с сохранением оригинального фрагмента текста
        для последующей подсветки.

        Args:
            text (str): Исходный текст.
            n (int): Длина шингла в словах.

        Returns:
            List[Dict]: Список объектов {query, original}.
        """
        # 1. Токенизация исходного текста (сохраняем слова)
        # Очищаем от лишних пробелов, но сохраняем структуру для поиска
        tokens = []
        raw_words = re.findall(r"\b\w+\b", text)

        processed_tokens = []
        for word in raw_words:
            lemma = word.lower()
            if morph:
                try:
                    p = morph.parse(lemma)[0]
                    lemma = p.normal_form
                except:
                    pass
            elif STEMMER:
                lemma = STEMMER.stem(lemma)

            is_stop = lemma in STOPWORDS or len(lemma) <= 2
            processed_tokens.append(
                {"original": word, "lemma": lemma, "is_stop": is_stop}
            )

        # 2. Формирование шинглов из не стоп-слов
        non_stop_indices = [
            i for i, t in enumerate(processed_tokens) if not t["is_stop"]
        ]

        if len(non_stop_indices) < n:
            return []

        shingles = []
        for i in range(len(non_stop_indices) - n + 1):
            window_indices = non_stop_indices[i : i + n]

            # Текст для поиска в XML (оригинальные слова для дословного поиска)
            query = " ".join(
                [processed_tokens[idx]["original"].lower() for idx in window_indices]
            )

            # Оригинальный фрагмент (от первого до последнего слова шингла включительно)
            start_idx = window_indices[0]
            end_idx = window_indices[-1]
            original_fragment = " ".join(
                [
                    processed_tokens[idx]["original"]
                    for idx in range(start_idx, end_idx + 1)
                ]
            )

            shingles.append({"query": query, "original": original_fragment})

        return shingles

    def check_shingle_xmlriver(self, shingle: str) -> Optional[List[Dict]]:
        """
        Отправляет запрос в XMLRiver (Яндекс) с текстом шингла и возвращает список URL
        и сниппетов, в которых найдено совпадение.

        Args:
            shingle (str): Текст шингла (фразы) для проверки.

        Returns:
            Optional[List[Dict]]: Список объектов {"url": ..., "snippet": ...} или None при ошибке.
        """
        if not self.user or not self.key:
            logger.error("Нет учетных данных для XMLRiver")
            return None

        # Формируем точный запрос в кавычках для поиска точного вхождения
        query = f'"{shingle}"'

        params = {
            "user": self.user,
            "key": self.key,
            "query": query,
            "lr": "213",  # Москва
            "lang": "ru",
            "domain": "ru",
            "device": "desktop",
            "groupby": "100",
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            data = xmltodict.parse(response.text)

            found_matches = []

            # Проверяем ошибки
            if "error" in data:
                error_node = data["error"]
                error_msg = error_node.get("#text") or error_node.get("@code")
                logger.warning(f"Ошибка API XMLRiver: {error_msg}")
                return None

            # Разбор ответа Yandex XML
            if "yandexsearch" in data:
                response_data = data["yandexsearch"].get("response", {})
                results = response_data.get("results", {})
                grouping = results.get("grouping", {})
                groups = grouping.get("group", [])

                if isinstance(groups, dict):
                    groups = [groups]

                for group in groups:
                    doc = group.get("doc", {})
                    url = doc.get("url")
                    if not url:
                        continue

                    def get_full_text(node):
                        if isinstance(node, str):
                            return node
                        if isinstance(node, list):
                            return " ".join([get_full_text(i) for i in node])
                        if isinstance(node, dict):
                            # Собираем всё: и hlword, и обычный текст
                            parts = []
                            for k, v in node.items():
                                if k in ["#text", "hlword"]:
                                    parts.append(get_full_text(v))
                            return " ".join(parts)
                        return str(node)

                    snippet = ""
                    passages_node = doc.get("passages", {})
                    if passages_node:
                        p_list = passages_node.get("passage", [])
                        if not isinstance(p_list, list):
                            p_list = [p_list]
                        snippet = " | ".join([get_full_text(p) for p in p_list])

                    if not snippet:
                        snippet = get_full_text(doc.get("title", ""))

                    found_matches.append({"url": url, "snippet": snippet})

            return found_matches

        except Exception as e:
            logger.error(f"Ошибка при запросе к XMLRiver для фразы '{shingle}': {e}")
            return None

    def fetch_page_text(self, url: str, timeout: int = 10) -> Optional[str]:
        """
        Получает текстовое содержимое страницы по URL.

        Args:
            url (str): URL страницы.
            timeout (int): Таймаут запроса в секундах.

        Returns:
            Optional[str]: Текст страницы или None при ошибке.
        """
        try:
            # Пытаемся импортировать BeautifulSoup
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning(
                "BeautifulSoup не установлен. Верификация контента недоступна."
            )
            return None

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Удаляем скрипты, стили и навигацию
            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()

            # Извлекаем текст
            text = soup.get_text(separator=" ", strip=True)
            logger.info(f"Получен текст страницы {url}: {len(text)} символов")
            return text

        except requests.RequestException as e:
            logger.warning(f"Ошибка при получении страницы {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при парсинге {url}: {e}")
            return None

    def verify_with_page_content(
        self, original_text: str, page_text: str
    ) -> Tuple[float, int, int]:
        """
        Сравнивает оригинальный текст с текстом страницы.

        Args:
            original_text (str): Исходный текст пользователя.
            page_text (str): Текст, полученный со страницы.

        Returns:
            Tuple[float, int, int]: (процент совпадения, кол-во совпавших шинглов, всего шинглов)
        """

        def normalize_text(text: str, remove_mode: str = "space") -> str:
            """
            Нормализует текст.
            remove_mode="space": заменяет пунктуацию на пробелы (Напр. "5-7" -> "5 7")
            remove_mode="empty": полностью удаляет пунктуацию (Напр. "5-7" -> "57")
            """
            text = text.lower()
            # Заменяем все пробельные символы (включая неразрывные) на обычные пробелы
            text = re.sub(r"[\s\u00a0\u2003\u2002\u2009]+", " ", text)

            if remove_mode == "space":
                # Заменяем пунктуацию на пробелы (для случаев типа "5-7" -> "5 7")
                text = re.sub(r"[^\w\s]", " ", text)
            else:
                # Полностью удаляем пунктуацию (для случаев типа "5-7" -> "57")
                text = re.sub(r"[^\w\s]", "", text)

            # Убираем множественные пробелы
            text = re.sub(r"\s+", " ", text).strip()
            return text

        # Генерируем шинглы из оригинального текста.
        # Используем n=3 для верификации (более строгая проверка)
        original_shingles = self.get_shingles(original_text, n=3)
        if not original_shingles:
            return (0.0, 0, 0, [], [])

        # Нормализуем текст страницы ДВУМЯ способами для максимального охвата
        page_text_space = normalize_text(page_text, remove_mode="space")
        page_text_empty = normalize_text(page_text, remove_mode="empty")

        matched_shingles = []
        unmatched_shingles = []
        for shingle in original_shingles:
            # Нормализуем фразу шингла (всегда в режиме space,
            # так как get_shingles уже разбил слова по границам)
            phrase = normalize_text(shingle["original"], remove_mode="space")

            # Проверяем вхождение в любой из вариантов текста страницы
            if phrase in page_text_space or phrase in page_text_empty:
                matched_shingles.append(shingle["original"])
            else:
                unmatched_shingles.append(shingle["original"])
                logger.debug(
                    f"Шингл '{shingle['original']}' не найден на странице (ни в space, ни в empty варианте)"
                )

        total = len(original_shingles)
        matched_count = len(matched_shingles)
        match_percent = (matched_count / total) * 100 if total > 0 else 0.0

        logger.info(
            f"Верификация: {matched_count}/{total} шинглов найдено на странице ({match_percent:.2f}%)"
        )
        return (
            match_percent,
            matched_count,
            total,
            matched_shingles,
            unmatched_shingles,
        )

    def get_estimated_cost(
        self,
        text: str,
        shingle_len: int = 4,
        shingle_step: int = 3,
        sampling_mode: str = "deterministic",
    ) -> Dict:
        """
        Предварительно рассчитывает стоимость проверки с учетом кеша и режима выборки.
        """
        import hashlib
        import math
        from app.db.uniqueness_db import get_cached_shingles
        from app.db.settings_db import get_setting

        all_shingles = self.get_shingles(text, n=shingle_len)
        if not all_shingles:
            return {"total": 0, "cached": 0, "to_pay": 0}

        # 1. Считаем хэши для ВСЕХ шинглов, чтобы максимизировать использование кеша
        for item in all_shingles:
            item["hash"] = hashlib.sha1(
                item["original"].lower().encode("utf-8")
            ).hexdigest()

        all_hashes = [item["hash"] for item in all_shingles]

        # Получаем срок жизни кеша из настроек
        ttl_days = int(get_setting("UNIQUENESS_CACHE_TTL") or 14)
        cache_results = get_cached_shingles(
            all_hashes, shingle_len=shingle_len, ttl_days=ttl_days
        )

        # 2. Выбираем шинглы, которые мы БЫ отправили в API (учитывая шаг)
        shingles_to_check = []
        if sampling_mode == "deterministic":
            # Детерминированная выборка: хэш каждого шингла определяет, проверять его или нет
            for item in all_shingles:
                if int(item["hash"], 16) % shingle_step == 0:
                    shingles_to_check.append(item)
        else:
            # Последовательная выборка (классическая)
            shingles_to_check = all_shingles[::shingle_step]

        total = len(shingles_to_check)

        # 3. Считаем, сколько из ВЫБРАННЫХ шинглов уже есть в кеше
        cached_count = 0
        for item in shingles_to_check:
            if item["hash"] in cache_results:
                cached_count += 1

        api_to_pay = total - cached_count

        # 4. Расчет стоимости кеша с учетом скидки
        try:
            discount = int(get_setting("UNIQUENESS_CACHE_DISCOUNT") or 0)
        except:
            discount = 0

        cached_to_pay = 0
        if discount > 0:
            # (из кеша - скидка в процентах (округляем до целого в меньшую сторону))
            # Т.е. если скидка 20%, то платим 80% от количества в кеше
            cached_to_pay = math.floor(cached_count * (100 - discount) / 100)
        else:
            # "если 0 то шинглы из кеша не тарифицируются"
            cached_to_pay = 0

        total_to_pay = api_to_pay + cached_to_pay

        return {
            "total": total,
            "cached": cached_count,
            "to_pay": max(0, total_to_pay),
            "api_to_pay": api_to_pay,
            "cached_to_pay": cached_to_pay,
            "discount": discount,
        }

    def check_text(
        self,
        text: str,
        shingle_len: int = 4,
        stride: int = 3,
        verify_content: bool = False,
        sampling_mode: str = "deterministic",
    ) -> Dict:
        """
        Проверяет уникальность текста (однопоточная версия).
        """
        import hashlib
        from app.db.uniqueness_db import get_cached_shingles

        all_shingles = self.get_shingles(text, n=shingle_len)
        if not all_shingles:
            return {"score": 0, "error": "Текст слишком короткий"}

        # 1. Хэшируем все
        for item in all_shingles:
            item["hash"] = hashlib.sha1(
                item["original"].lower().encode("utf-8")
            ).hexdigest()

        # 2. Выборка
        if sampling_mode == "deterministic":
            shingles_to_check = [
                item for item in all_shingles if int(item["hash"], 16) % stride == 0
            ]
        else:
            shingles_to_check = all_shingles[::stride]

        total_attempted = len(shingles_to_check)
        actual_successful_requests = 0
        non_unique_count = 0
        matches = []

        logger.info(
            f"Начало проверки (однопоточно). Режим: {sampling_mode}. "
            f"Всего шинглов: {len(all_shingles)}, выбрано: {total_attempted}"
        )

        # 3. Кеш (передаем shingle_len и ttl_days)
        from app.db.settings_db import get_setting

        ttl_days = int(get_setting("UNIQUENESS_CACHE_TTL") or 14)
        hashes_to_check = [item["hash"] for item in shingles_to_check]
        cache_results = get_cached_shingles(
            hashes_to_check, shingle_len=shingle_len, ttl_days=ttl_days
        )

        to_query = []
        for item in shingles_to_check:
            h = item["hash"]
            if h in cache_results:
                found_data = cache_results[h]["found_urls"]
                actual_successful_requests += 1
                if found_data:
                    non_unique_count += 1
                    matches.append(
                        {
                            "shingle": item["query"],
                            "original": item["original"],
                            "urls": found_data,
                            "cached": True,
                        }
                    )
            else:
                to_query.append(item)

        # 4. API запросы (последовательно)
        for item in to_query:
            found_urls = self.check_shingle_xmlriver(item["query"])
            actual_successful_requests += 1
            if found_urls is not None:
                if found_urls:
                    non_unique_count += 1
                    matches.append(
                        {
                            "shingle": item["query"],
                            "original": item["original"],
                            "urls": found_urls,
                            "cached": False,
                        }
                    )
            else:
                # Ошибка API
                pass

        score = 100
        if actual_successful_requests > 0:
            score = round(
                (
                    (actual_successful_requests - non_unique_count)
                    / actual_successful_requests
                )
                * 100,
                2,
            )

        result = {
            "score": score,
            "matches": matches,
            "total_shingles": len(all_shingles),
            "checked_shingles": actual_successful_requests,
        }

        # Этап 2: Верификация
        if verify_content and matches:
            result = self.verify_result_content(text, result)

        return result

    def verify_result_content(self, text: str, result: Dict) -> Dict:
        """Вспомогательный метод для верификации контента страницы."""
        matches = result.get("matches", [])
        if not matches:
            return result

        logger.info("Запуск верификации по контенту страницы...")

        # Находим страницу с наибольшим количеством совпадений
        url_counts = {}
        for match in matches:
            for url in match.get("urls", []):
                url_counts[url] = url_counts.get(url, 0) + 1

        if url_counts:
            # Берём URL с максимальным числом совпадений
            top_url = max(url_counts, key=url_counts.get)
            top_url_count = url_counts[top_url]
            logger.info(
                f"Страница с максимальным совпадением: {top_url} ({top_url_count} шинглов)"
            )

            # Получаем текст страницы
            page_text = self.fetch_page_text(top_url)

            if page_text:
                # Верифицируем
                (
                    match_percent,
                    matched_count,
                    total_shingles_count,
                    matched_list,
                    unmatched_list,
                ) = self.verify_with_page_content(text, page_text)

                # Пересчитываем уникальность: 100% - % совпадений
                verified_score = round(100 - match_percent, 2)

                result["verified_url"] = top_url
                result["verified_score"] = verified_score
                result["verified_matched_shingles"] = matched_count
                result["verified_total_shingles"] = total_shingles_count
                # Список совпавших фрагментов для подсветки на UI
                result["verified_matches"] = matched_list
                result["original_score"] = result["score"]
                result["score"] = verified_score

                logger.info(
                    f"Верификация завершена. Скорректированная уникальность: {verified_score}%"
                )
            else:
                result["verification_error"] = (
                    f"Не удалось получить контент страницы {top_url}"
                )
                logger.warning(result["verification_error"])
        return result

    def check_text_multithreaded(
        self,
        text: str,
        shingle_len: int = 4,
        stride: int = 3,
        threads: int = 5,
        verify_content: bool = False,
        task_id: str = None,
        sampling_mode: str = "deterministic",
    ) -> Dict:
        """
        Проверяет уникальность текста в несколько потоков.

        Args:
            text (str): Исходный текст.
            shingle_len (int): Длина шингла.
            stride (int): Шаг проверки.
            threads (int): Количество потоков.
            verify_content (bool): Верифицировать ли контент.
            task_id (str): ID задачи для обновления прогресса в БД.
        """
        from app.db.uniqueness_db import (
            update_uniqueness_task_progress,
            complete_uniqueness_task,
            set_uniqueness_task_error,
            get_cached_shingles,
            update_shingles_cache,
            refund_user_limits,
            save_analytics_record,
        )

        all_shingles = self.get_shingles(text, n=shingle_len)
        if not all_shingles:
            error_data = {"score": 0, "error": "Текст слишком короткий"}
            if task_id:
                set_uniqueness_task_error(task_id, error_data["error"])
            return error_data

        # 1. Подготавливаем хэши для ВСЕХ шинглов (максимально используем кеш)
        for item in all_shingles:
            item["text_to_query"] = item["original"].lower()
            item["hash"] = hashlib.sha1(
                item["text_to_query"].encode("utf-8")
            ).hexdigest()

        # 2. Выбираем шинглы для проверки в зависимости от режима
        if sampling_mode == "deterministic":
            # Выбираем те, чьи хэши кратны шагу
            shingles_to_check = [
                item for item in all_shingles if int(item["hash"], 16) % stride == 0
            ]
        else:
            # Классический шаг (каждый N-й)
            shingles_to_check = all_shingles[::stride]

        total_attempted = len(shingles_to_check)
        actual_successful_requests = 0
        non_unique_count = 0
        matches = []

        hashes_to_check = [item["hash"] for item in shingles_to_check]

        logger.info(
            f"Начало многопоточной проверки ({threads} потоков). Режим: {sampling_mode}. "
            f"Всего шинглов: {len(all_shingles)}, выбрано для API: {total_attempted}"
        )

        # --- ЭТАП 1: Проверка Кэша (передаем shingle_len и ttl_days) ---
        from app.db.settings_db import get_setting

        ttl_days = int(get_setting("UNIQUENESS_CACHE_TTL") or 14)
        # Получаем данные из кеша
        cache_results = get_cached_shingles(
            hashes_to_check, shingle_len=shingle_len, ttl_days=ttl_days
        )

        to_query = []
        cache_hits_count = 0

        for item in shingles_to_check:
            h = item["hash"]
            if h in cache_results:
                # Берем из кеша
                found_data = cache_results[h]["found_urls"]
                actual_successful_requests += 1
                cache_hits_count += 1
                if found_data:
                    non_unique_count += 1
                    matches.append(
                        {
                            "shingle": item["query"],
                            "original": item["original"],
                            "urls": found_data,
                            "cached": True,
                        }
                    )
            else:
                to_query.append(item)

        logger.info(
            f"Кеш: найдено {cache_hits_count} из {total_attempted}. К запросу API: {len(to_query)}"
        )

        # --- ЭТАП 2: Запросы к API (только для Cache Miss) ---
        new_cache_entries = []

        with ThreadPoolExecutor(max_workers=threads) as executor:
            # Создаем словарь {future: shingle_data}
            future_to_shingle = {
                executor.submit(
                    self.check_shingle_xmlriver, item["text_to_query"]
                ): item
                for item in to_query
            }

            completed_count = cache_hits_count
            for future in as_completed(future_to_shingle):
                item = future_to_shingle[future]
                completed_count += 1

                # Обновляем прогресс в БД
                if task_id and completed_count % 2 == 0:
                    update_uniqueness_task_progress(task_id, completed_count)

                try:
                    found_data = future.result()
                    if found_data is not None:
                        actual_successful_requests += 1
                        urls = [m["url"] for m in found_data]

                        # Сохраняем для обновления кеша
                        new_cache_entries.append(
                            (item["hash"], json.dumps(urls), len(urls) == 0)
                        )

                        if len(found_data) > 0:
                            non_unique_count += 1
                            matches.append(
                                {
                                    "shingle": item["query"],
                                    "original": item["original"],
                                    "urls": urls,
                                }
                            )
                    else:
                        logger.warning(f"Ошибка API для шингла '{item['query']}'")
                except Exception as exc:
                    logger.error(
                        f"Поток сгенерировал исключение для '{item['query']}': {exc}"
                    )

        # Сохраняем новые данные в кеш (передаем shingle_len)
        if new_cache_entries:
            update_shingles_cache(new_cache_entries, shingle_len=shingle_len)

        # Возвращаем «лишние» зарезервированные лимиты пользователю
        # Лимиты могли остаться, если API вернуло ошибку для части шинглов
        # или если в кеше оказалось больше данных, чем было при оценке стоимости.
        if task_id:
            try:
                from app.db.settings_db import get_setting
                import math

                # Получаем текущую скидку
                try:
                    discount = int(get_setting("UNIQUENESS_CACHE_DISCOUNT") or 0)
                except:
                    discount = 0

                conn = create_connection()
                if conn:
                    cur = conn.cursor(dictionary=True)
                    # Находим сколько было зарезервировано и кто владелец
                    cur.execute(
                        "SELECT user_id, reserved_limits FROM uniqueness_tasks WHERE task_id = %s",
                        (task_id,),
                    )
                    task_info = cur.fetchone()

                    if task_info and task_info["user_id"]:
                        # 1. Считаем реальную стоимость API-запросов
                        api_calls_count = max(
                            0, actual_successful_requests - cache_hits_count
                        )

                        # 2. Считаем стоимость кеша с учетом скидки
                        actual_cache_cost = 0
                        if discount > 0:
                            actual_cache_cost = math.floor(
                                cache_hits_count * (100 - discount) / 100
                            )
                        else:
                            actual_cache_cost = 0

                        # 3. Итоговая реальная стоимость
                        final_total_cost = api_calls_count + actual_cache_cost

                        # Логируем статистику (как просил пользователь)
                        logger.info(
                            f"=== Статистика задачи {task_id} ===\n"
                            f"Всего шинглов в тексте: {len(all_shingles)}\n"
                            f"Выбрано для проверки (с учетом шага): {total_attempted}\n"
                            f"Проверено успешно (всего): {actual_successful_requests}\n"
                            f"Из них по API: {api_calls_count}\n"
                            f"Найдено в кеше: {cache_hits_count}\n"
                            f"Итого списано лимитов: {final_total_cost} (API: {api_calls_count} + Кеш: {actual_cache_cost} [скидка {discount}%])\n"
                            f"Зарезервировано было: {task_info['reserved_limits']}\n"
                            f"===================================="
                        )

                        # 4. Корректируем лимиты пользователя
                        if task_info["reserved_limits"] > final_total_cost:
                            refund_amount = (
                                task_info["reserved_limits"] - final_total_cost
                            )

                            cur.execute(
                                "UPDATE users SET limits = limits + %s WHERE id = %s",
                                (refund_amount, task_info["user_id"]),
                            )
                            cur.execute(
                                "UPDATE uniqueness_tasks SET reserved_limits = %s WHERE task_id = %s",
                                (final_total_cost, task_id),
                            )
                            conn.commit()
                            logger.info(
                                f"Корректировка лимитов задачи {task_id}: возвращено {refund_amount} излишков. Итоговая стоимость: {final_total_cost}"
                            )
                        elif task_info["reserved_limits"] < final_total_cost:
                            # Обновляем статистику, но не списываем доп. лимиты (чтобы не пугать пользователя)
                            cur.execute(
                                "UPDATE uniqueness_tasks SET reserved_limits = %s WHERE task_id = %s",
                                (final_total_cost, task_id),
                            )
                            conn.commit()

                    cur.close()
                    conn.close()
            except Exception as e:
                logger.error(f"Ошибка при корректировке лимитов задачи {task_id}: {e}")

        # Финальный прогресс
        if task_id:
            update_uniqueness_task_progress(
                task_id, total_attempted, status="completed"
            )

        # --- ФИЛЬТРАЦИЯ И ОПТИМИЗАЦИЯ РЕЗУЛЬТАТОВ ---
        # 1. Посчитаем статистику по всем найденным URL
        url_stats = {}
        for m in matches:
            for u in m["urls"]:
                url_stats[u] = url_stats.get(u, 0) + 1

        from app.db.settings_db import get_setting

        try:
            min_percent = int(get_setting("UNIQUENESS_MIN_MATCH_PERCENT") or 2)
            max_urls = int(get_setting("UNIQUENESS_MAX_MATCH_URLS") or 100)
        except:
            min_percent = 2
            max_urls = 100

        # 2. Фильтруем URL по порогу % совпадения
        valid_urls_list = []
        for url, count in url_stats.items():
            match_percent = (count / total_attempted) * 100
            if match_percent >= min_percent:
                valid_urls_list.append(
                    {"url": url, "count": count, "percent": match_percent}
                )

        # 3. Сортируем по убыванию совпадений и ограничиваем количество
        valid_urls_list.sort(key=lambda x: x["count"], reverse=True)
        valid_urls_list = valid_urls_list[:max_urls]

        # Множество разрешенных URL для быстрой очистки матчей
        allowed_urls = {item["url"] for item in valid_urls_list}

        # 4. Очищаем matches от URL, не прошедших фильтр
        # (ОЧЕНЬ ВАЖНО: не пересчитываем non_unique_count, так как он относится ко всем совпадениям в поиске)
        optimized_matches = []
        for m in matches:
            m["urls"] = [u for u in m["urls"] if u in allowed_urls]
            if m["urls"]:
                optimized_matches.append(m)

        matches = optimized_matches

        if actual_successful_requests == 0:
            error_data = {"score": 0, "error": "Не удалось выполнить запросы к API."}
            if task_id:
                set_uniqueness_task_error(task_id, error_data["error"])
            return error_data

        unique_percent = (
            (actual_successful_requests - non_unique_count) / actual_successful_requests
        ) * 100

        result = {
            "score": round(unique_percent, 2),
            "matches": matches,
            "top_urls": valid_urls_list,  # Предварительно рассчитанные сайты
            "total_shingles": len(all_shingles),
            "checked_shingles": actual_successful_requests,
            "attempted_shingles": total_attempted,
            "non_unique_shingles": non_unique_count,
        }

        if verify_content and matches:
            result = self.verify_result_content(text, result)

        if task_id:
            complete_uniqueness_task(task_id, result)

            # Сохраняем данные в персистентную таблицу аналитики
            # (не зависит от удаления задач или пользователей)
            try:
                # Получаем user_id из задачи для записи аналитики
                from app.db.uniqueness_db import get_uniqueness_task

                task_data = get_uniqueness_task(task_id)
                analytics_user_id = task_data["user_id"] if task_data else None

                # Считаем реальное количество API-вызовов
                api_calls_for_analytics = max(
                    0, actual_successful_requests - cache_hits_count
                )

                # Финальная стоимость лимитов (из задачи, после корректировок)
                limits_final = (task_data or {}).get("reserved_limits", 0)

                save_analytics_record(
                    task_id,
                    analytics_user_id,
                    {
                        "score": result["score"],
                        "total_shingles": len(all_shingles),
                        "checked_shingles": actual_successful_requests,
                        "non_unique_shingles": non_unique_count,
                        "cache_hits": cache_hits_count,
                        "api_calls": api_calls_for_analytics,
                        "limits_spent": limits_final,
                        "text_length": len(text),
                        "top_urls": result["top_urls"],
                    },
                )
            except Exception as e:
                logger.error(f"Ошибка при сохранении аналитики задачи {task_id}: {e}")

        return result
