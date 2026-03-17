import json
from urllib.parse import urlparse
from collections import Counter
from app.db.database import create_connection
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_results(xml_result: dict, project_url: str) -> dict:
    """
    Анализирует результат от XmlRiver и ищет позицию домена проекта.

    :param xml_result: JSON-ответ от API XmlRiver.
    :param project_url: URL-адрес проекта для поиска.
    :return: Словарь с позицией, найденным URL и топ-10 URL.
    """
    position = None
    url_found = None
    top_10_urls = []

    if 'items' in xml_result:
        items = xml_result['items']
        top_10_urls = [item.get('url') for item in items[:10]]

        for i, item in enumerate(items):
            if project_url in item.get('url', ''):
                position = i + 1
                url_found = item.get('url')
                break

    return {
        'position': position,
        'url_found': url_found,
        'top_10_urls': top_10_urls
    }

def get_top_competitors(project_id: int, variant_id: int, date: str) -> list:
    """
    Собирает и анализирует топ-10 URL конкурентов для заданного проекта, варианта и даты.

    Args:
        project_id (int): ID проекта.
        variant_id (int): ID варианта парсинга.
        date (str): Дата для анализа в формате 'YYYY-MM-DD'.

    Returns:
        list: Отсортированный список кортежей [('domain', count), ...].
    
    Raises:
        ValueError: Если проект не найден.
    """
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # 1. Получить URL проекта
        cursor.execute("SELECT url FROM projects WHERE id = %s", (project_id,))
        project_row = cursor.fetchone()
        if not project_row:
            raise ValueError(f"Проект с ID {project_id} не найден.")
        project_domain = urlparse(project_row['url']).netloc

        # 2. Получить топ-10 URL
        sql_query = """
            SELECT top_10_urls
            FROM parsing_position_results
            WHERE parsing_variant_id = %s AND DATE(date) = %s
        """
        cursor.execute(sql_query, (variant_id, date))
        results = cursor.fetchall()

        # Дальнейшая логика на Python
        all_urls = []
        for row in results:
            if row['top_10_urls']:
                # Десериализация JSON
                urls = json.loads(row['top_10_urls'])
                all_urls.extend(urls)

        # Извлечь домены и подсчитать их частоту
        domain_counts = Counter(
            urlparse(url).netloc for url in all_urls if url and urlparse(url).netloc
        )

        # Исключить домен самого проекта
        if project_domain in domain_counts:
            del domain_counts[project_domain]

        return domain_counts.most_common()

    except Exception as e:
        logger.error(f"Ошибка при получении топ-конкурентов: {e}")
        # Перехватываем и снова выбрасываем исключение, чтобы вызывающий код мог его обработать
        raise e
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_domain_from_url(url_str: str) -> str:
    """Извлекает чистый домен из URL."""
    if not url_str:
        return ""
    try:
        parsed = urlparse(url_str.lower())
        return parsed.netloc.replace("www.", "").rstrip("/")
    except Exception as e:
        logger.error(f"Ошибка извлечения домена из URL '{url_str}': {e}")
        return ""