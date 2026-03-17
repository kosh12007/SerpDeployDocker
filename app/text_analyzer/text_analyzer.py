import requests
from bs4 import BeautifulSoup
import re
import nltk
from nltk.corpus import stopwords
import logging
import os
import math
from urllib.parse import urlparse
from app.db_config import LOGGING_ENABLED

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "text_analyzer.log")
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

# Загружаем стоп-слова (один раз)
nltk.download("stopwords", quiet=True)
STOP_WORDS_RU = stopwords.words("russian") + ["это", "который", "очень", "еще", "также"]


def analyze_text_content(text_content):
    """
    Анализирует текст и вычисляет метрики: количество символов (с пробелами и без),
    количество слов, "тошноту" и "заспамленность".

    Args:
        text_content (str): Текст для анализа

    Returns:
        dict: Словарь с результатами анализа
    """
    # Подсчет количества символов с пробелами
    chars_with_spaces = len(text_content)

    # Подсчет количества символов без пробелов
    chars_without_spaces = len(re.sub(r"\s", "", text_content))

    # Подсчет количества слов
    words = len(re.findall(r"\b\w+\b", text_content))

    # Вычисление "тошноты" (плотности вхождения ключевых слов)
    # Для этого нужно найти часто встречающиеся слова и вычислить их плотность
    word_list = re.findall(r"\b\w+\b", text_content.lower())
    total_words = len(word_list)

    # Подсчет частоты слов
    # Подсчет количества стоп-слов (води)
    stop_words_count = 0
    water_words = []

    # Создаем частотный словарь для всех слов (для тошноты и заспамленности)
    word_freq = {}
    for word in word_list:
        word_freq[word] = word_freq.get(word, 0) + 1
        if word in STOP_WORDS_RU:
            stop_words_count += 1
            water_words.append(word)

    # Создаем частотный словарь для стоп-слов
    stop_words_freq = {}
    for word in water_words:
        stop_words_freq[word] = stop_words_freq.get(word, 0) + 1

    # Генерация n-грамм (1, 2, 3 слова)
    def generate_ngrams(tokens, n):
        return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]

    # Получаем токены для n-грамм (исключаем стоп-слова для "ключевых слов")
    tokens = re.findall(r"\b\w+\b", text_content.lower())
    content_tokens = [t for t in tokens if t not in STOP_WORDS_RU]

    # 1-граммы (только значимые слова)
    content_word_freq = {w: f for w, f in word_freq.items() if w not in STOP_WORDS_RU}
    ngram_1 = sorted(content_word_freq.items(), key=lambda x: x[1], reverse=True)[:50]

    # 2-граммы (на основе последовательностей без стоп-слов)
    bigrams = generate_ngrams(content_tokens, 2)
    bigram_freq = {}
    for bg in bigrams:
        bigram_freq[bg] = bigram_freq.get(bg, 0) + 1
    ngram_2 = sorted(bigram_freq.items(), key=lambda x: x[1], reverse=True)[:50]

    # 3-граммы (на основе последовательностей без стоп-слов)
    trigrams = generate_ngrams(content_tokens, 3)
    trigram_freq = {}
    for tg in trigrams:
        trigram_freq[tg] = trigram_freq.get(tg, 0) + 1
    ngram_3 = sorted(trigram_freq.items(), key=lambda x: x[1], reverse=True)[:50]

    # Сортируем стоп-слова по частоте для отдельной таблицы
    stop_ngram = sorted(stop_words_freq.items(), key=lambda x: x[1], reverse=True)[:50]

    if total_words == 0:
        water_percentage = 0
        nausea = 0
        spam_score = 0
    else:
        # Вычисление водности
        water_percentage = round((stop_words_count / total_words) * 100, 2)

        # Вычисление "Тошноты" (только для значимых слов)
        content_words = [w for w in word_list if w not in STOP_WORDS_RU]
        total_content_words = len(content_words)

        if content_word_freq and total_content_words > 0:
            max_freq_sig = max(content_word_freq.values())
            # Классическая тошнота = квадратный корень из максимальной частоты значимого слова
            classic_nausea = round(math.sqrt(max_freq_sig), 2)
            # Академическая тошнота = (макс. частота / общее кол-во значимых слов) * 100
            academic_nausea = round((max_freq_sig / total_content_words) * 100, 2)
        else:
            classic_nausea = 0
            academic_nausea = 0

        # Вычисление "заспамленности" на основе повторений (исключая стоп-слова)
        if total_content_words > 0:
            unique_content_words = len(set(content_words))
            repetition_rate = (
                total_content_words - unique_content_words
            ) / total_content_words
            spam_score = round(repetition_rate * 100, 2)
        else:
            spam_score = 0

    return {
        "chars_with_spaces": chars_with_spaces,
        "chars_without_spaces": chars_without_spaces,
        "word_count": words,
        "unique_word_count": len(
            set(word_list)
        ),  # Подсчет количества уникальных слов (регистронезависимо)
        "water_percentage": water_percentage,
        "classic_nausea": classic_nausea,
        "academic_nausea": academic_nausea,
        "spam_score": spam_score,
        "word_frequency": word_freq,
        "content_word_frequency": content_word_freq,
        "total_words": total_words,
        "water_words": water_words,  # список стоп-слов для подсветки
        "top_ngrams": {
            "1_word": ngram_1,
            "2_words": ngram_2,
            "3_words": ngram_3,
            "stop_words": stop_ngram,
        },
    }


def extract_text_from_url(url):
    """
    Извлекает текст со страницы по URL.

    Args:
        url (str): URL страницы для анализа

    Returns:
        str: Извлеченный текст или пустая строка в случае ошибки
    """
    try:
        # Проверяем валидность URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Неверный формат URL")

        headers = {"User-Agent": "Mozilla/5.0 (compatible; TextAnalyzer/1.0)"}
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Извлекаем текст из тегов <p>, <h1>-<h6>, <li>, <div> (с текстом)
        # Для сохранения структуры будем искать основные блочные элементы
        blocks = soup.find_all(
            ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "article", "section", "div"]
        )

        full_text_parts = []
        seen_text = set()  # Для дедупликации, если блоки вложены

        for block in blocks:
            # Пропускаем вложенные блоки, если их родитель уже обработан (упрощенно)
            # Но проще брать только текст непосредственного блока, если он значим
            # Или просто брать get_text с separator
            pass

        # Более простой и надежный способ сохранить структуру - использовать get_text с разделителем
        # Но нам нужно почистить мусор.

        # Попробуем альтернативный подход: итерируемся по блокам
        # text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])

        # Чтобы не усложнять, используем простой get_text и постобработку, но это убьет абзацы если не задать separator
        # full_text = soup.get_text(separator='\n')

        # Возвращаемся к логике с выборкой параграфов, но добавляем заголовки
        text_tags = soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"])

        processed_text = ""

        for tag in text_tags:
            text = tag.get_text().strip()
            if not text:
                continue

            # Простая очистка
            cleaned = re.sub(r"\s+", " ", text)
            # cleaned = re.sub(r"[^a-zA-Zа-яА-Я0-9\s\.\,\!\?\-\:]", "", cleaned) # Оставляем пунктуацию для читаемости

            if len(cleaned.split()) > 0:
                processed_text += cleaned + "\n\n"

        return processed_text.strip()
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(f"Ошибка при извлечении текста из URL {url}: {e}")
        return ""


def analyze_url_or_text(input_source, is_url=True):
    """
    Анализирует либо URL, либо прямой текст в зависимости от параметра is_url.

    Args:
        input_source (str): URL или текст для анализа
        is_url (bool): Если True, считается что input_source - это URL, иначе текст

    Returns:
        dict: Результаты анализа
    """
    text_content = ""
    if is_url:
        # Извлечение текста с веб-страницы
        text_content = extract_text_from_url(input_source)
        if not text_content:
            return {
                "error": f"Не удалось получить текст со страницы: проверьте URL и доступность ресурса."
            }

    else:
        # Прямой текст
        text_content = input_source.strip()

    # Анализируем текст
    analysis_result = analyze_text_content(text_content)
    analysis_result["input_type"] = "URL" if is_url else "Text"

    # Возвращаем также исходный текст для отображения (с форматированием)
    analysis_result["text_content"] = text_content

    return analysis_result
