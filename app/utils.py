import logging
import os
from collections import Counter
from app.db_config import LOGGING_ENABLED
from app.config import Config

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "utils.log")
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


def assign_duplicate_styles(all_urls):
    """
    Находит дублирующиеся URL и назначает им циклически CSS-классы для подсветки.
    Принимает плоский список URL.
    Возвращает словарь, где ключ - URL, значение - CSS-класс.
    """
    if LOGGING_ENABLED:
        logger.debug(f"На вход assign_duplicate_styles подан список URL: {all_urls}")

    url_counts = Counter(all_urls)
    if LOGGING_ENABLED:
        logger.debug(f"Счетчик URL: {url_counts}")

    duplicated_urls = [url for url, count in url_counts.items() if count > 1]
    if LOGGING_ENABLED:
        logger.debug(f"Найденные дубликаты URL: {duplicated_urls}")

    style_classes = [
        "bg-red-200",
        "bg-blue-200",
        "bg-green-200",
        "bg-yellow-200",
        "bg-purple-200",
        "bg-pink-200",
        "bg-indigo-200",
        "bg-teal-200",
        "bg-orange-200",
        "bg-gray-300",
        "bg-red-300",
        "bg-blue-300",
        "bg-green-300",
        "bg-yellow-300",
        "bg-purple-300",
        "bg-pink-300",
        "bg-indigo-300",
        "bg-teal-300",
        "bg-orange-300",
        "bg-gray-400",
        "bg-lime-200",
        "bg-cyan-200",
        "bg-fuchsia-200",
        "bg-rose-200",
        "bg-sky-200",
        "bg-amber-200",
        "bg-emerald-200",
        "bg-violet-200",
        "bg-fuchsia-300",
        "bg-rose-300",
    ]

    duplicate_styles = {}
    for i, url in enumerate(duplicated_urls):
        duplicate_styles[url] = style_classes[i % len(style_classes)]
    if LOGGING_ENABLED:
        logger.debug(
            f"Сформированный словарь стилей для дубликатов: {duplicate_styles}"
        )

    return duplicate_styles
