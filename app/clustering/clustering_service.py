import json
from urllib.parse import urlparse
from ..db.database import create_connection
import logging
import os
from app.db_config import LOGGING_ENABLED

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "clustering_service.log")
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


class HardClusterizer:
    """
    Сервисный класс для выполнения Hard-кластеризации ключевых слов.
    """

    def __init__(self, project_id, threshold):
        """
        Инициализирует кластеризатор.

        :param project_id: ID проекта, для которого выполняется кластеризация.
        :param threshold: Минимальное количество общих URL для объединения в группу.
        """
        if not isinstance(project_id, int) or project_id <= 0:
            raise ValueError("ID проекта должен быть положительным целым числом.")
        if not isinstance(threshold, int) or not 2 <= threshold <= 10:
            raise ValueError("Порог должен быть целым числом от 2 до 10.")

        self.project_id = project_id
        self.threshold = threshold
        self.connection = create_connection()
        self.keywords_data = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            if LOGGING_ENABLED:
                logger.info("Соединение с базой данных закрыто.")

    def _normalize_url(self, url):
        """
        Приводит URL к каноническому виду для сравнения.
        - Убирает протокол (http, https)
        - Убирает 'www.'
        - Убирает завершающий слэш
        """
        if not url:
            return ""
        try:
            p = urlparse(url)
            domain = p.netloc.replace("www.", "").lower()
            path = p.path.rstrip("/")
            return f"{domain}{path}"
        except Exception as e:
            if LOGGING_ENABLED:
                logger.warning(f"Не удалось нормализовать URL '{url}': {e}")
            return ""

    def load_keywords_with_serps(self):
        """
        Загружает ключевые слова и их ТОП-10 URL из базы данных.
        Берет самые свежие данные для каждого ключевого слова.
        """
        if LOGGING_ENABLED:
            logger.info(f"Загрузка данных для проекта ID: {self.project_id}")
        cursor = self.connection.cursor(dictionary=True)

        # SQL-запрос для получения последнего результата парсинга для каждого ключевого слова
        # Используем оконную функцию ROW_NUMBER() для нумерации записей
        query = """
            SELECT
                q.id,
                q.query_text as name,
                q.frequency as volume,
                ppr.top_10_urls
            FROM queries q
            JOIN parsing_position_results ppr ON q.id = ppr.query_id
            INNER JOIN (
                SELECT
                    query_id,
                    MAX(created_at) AS max_created_at
                FROM parsing_position_results
                GROUP BY query_id
            ) AS latest ON ppr.query_id = latest.query_id AND ppr.created_at = latest.max_created_at
            WHERE q.project_id = %s AND ppr.top_10_urls IS NOT NULL AND ppr.top_10_urls != '[]';
        """
        try:
            cursor.execute(query, (self.project_id,))
            raw_data = cursor.fetchall()

            for row in raw_data:
                try:
                    # top_10_urls хранится как JSON-строка
                    urls_list = json.loads(row["top_10_urls"])
                    normalized_urls = {
                        self._normalize_url(url) for url in urls_list if url
                    }

                    self.keywords_data.append(
                        {
                            "id": row["id"],
                            "name": row["name"],
                            "volume": row["volume"] or 0,
                            "urls_set": normalized_urls,
                        }
                    )
                except (json.JSONDecodeError, TypeError) as e:
                    if LOGGING_ENABLED:
                        logger.warning(
                            f"Ошибка декодирования JSON для ключа ID {row['id']}: {e}"
                        )

        except Exception as e:
            if LOGGING_ENABLED:
                logger.error(f"Ошибка при загрузке данных из БД: {e}", exc_info=True)
            raise
        finally:
            cursor.close()

        if LOGGING_ENABLED:
            logger.info(f"Загружено {len(self.keywords_data)} ключевых слов с SERP.")

    @staticmethod
    def move_keyword_to_group(keyword_id, target_group_id):
        sql = "UPDATE queries SET query_group_id = %s WHERE id = %s;"
        with create_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (target_group_id, keyword_id))
                conn.commit()

    @staticmethod
    def rename_group(group_id, new_name):
        sql = "UPDATE query_groups SET name = %s WHERE id = %s;"
        with create_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (new_name, group_id))
                conn.commit()

    @staticmethod
    def delete_group(group_id):
        # Сначала "отвязываем" все ключевые слова от этой группы
        sql_update = (
            "UPDATE queries SET query_group_id = NULL WHERE query_group_id = %s;"
        )
        # Затем удаляем саму группу
        sql_delete = "DELETE FROM query_groups WHERE id = %s;"
        with create_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_update, (group_id,))
                cursor.execute(sql_delete, (group_id,))
                conn.commit()

    @staticmethod
    def create_group(project_id, group_name):
        sql = "INSERT INTO query_groups (project_id, name) VALUES (%s, %s);"
        with create_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (project_id, group_name))
                conn.commit()
                return cursor.lastrowid

    def run_clustering(self):
        """
        Выполняет алгоритм Hard-кластеризации.
        """
        if not self.keywords_data:
            if LOGGING_ENABLED:
                logger.warning(
                    "Нет данных для кластеризации. Возможно, нужно запустить load_keywords_with_serps()."
                )
            return []

        # Сортируем ключевые слова по частотности (volume) в убывающем порядке
        sorted_kws = sorted(self.keywords_data, key=lambda x: x["volume"], reverse=True)

        clusters = []
        used_keyword_ids = set()

        # Проходим по отсортированным словам, используя их как маркеры (центры) кластеров
        for marker in sorted_kws:
            if marker["id"] in used_keyword_ids:
                continue

            # Создаем новый кластер с текущим маркером
            current_cluster = {"main_keyword": marker, "members": [marker]}
            used_keyword_ids.add(marker["id"])

            # Ищем кандидатов для добавления в этот кластер
            for candidate in sorted_kws:
                if candidate["id"] in used_keyword_ids:
                    continue

                # Проверяем условие Hard-кластеризации: пересечение множеств URL
                intersection_size = len(
                    marker["urls_set"].intersection(candidate["urls_set"])
                )
                if intersection_size >= self.threshold:
                    current_cluster["members"].append(candidate)
                    used_keyword_ids.add(candidate["id"])

            clusters.append(current_cluster)

        if LOGGING_ENABLED:
            logger.info(f"Кластеризация завершена. Создано {len(clusters)} кластеров.")
        return clusters

    def get_current_groups(self):
        """
        Получает текущую структуру групп из базы данных.
        """
        if LOGGING_ENABLED:
            logger.info(f"Получение текущих групп для проекта ID: {self.project_id}")
        cursor = self.connection.cursor(dictionary=True)

        # Сначала получаем сгруппированные ключевые слова
        query = """
            SELECT
                g.name AS group_name,
                g.id AS group_id,
                k.query_text AS keyword_name,
                k.frequency AS keyword_volume
            FROM query_groups g
            JOIN queries k ON g.id = k.query_group_id
            WHERE g.project_id = %s
            ORDER BY g.name, k.query_text;
        """
        try:
            cursor.execute(query, (self.project_id,))
            rows = cursor.fetchall()

            groups_map = {}
            for row in rows:
                group_name = row["group_name"]
                if group_name not in groups_map:
                    groups_map[group_name] = {
                        "id": row["group_id"],
                        "name": group_name,
                        "keywords": [],
                        "total_volume": 0,
                    }
                groups_map[group_name]["keywords"].append(row["keyword_name"])
                groups_map[group_name]["total_volume"] += row["keyword_volume"] or 0

            result = list(groups_map.values())

            # Теперь получаем некластеризованные ключевые слова (те, у которых query_group_id IS NULL)
            ungrouped_query = """
                SELECT
                    query_text AS keyword_name,
                    frequency AS keyword_volume
                FROM queries
                WHERE project_id = %s AND query_group_id IS NULL
                ORDER BY query_text;
            """
            cursor.execute(ungrouped_query, (self.project_id,))
            ungrouped_rows = cursor.fetchall()

            if ungrouped_rows:
                ungrouped_keywords = [row["keyword_name"] for row in ungrouped_rows]
                ungrouped_volume = sum(
                    row["keyword_volume"] or 0 for row in ungrouped_rows
                )

                result.append(
                    {
                        "id": None,  # У некластеризованных ключей нет ID группы
                        "name": "Некластеризованные запросы",
                        "keywords": ungrouped_keywords,
                        "total_volume": ungrouped_volume,
                    }
                )

            return result
        except Exception as e:
            if LOGGING_ENABLED:
                logger.error(f"Ошибка при получении текущих групп: {e}", exc_info=True)
            return []
        finally:
            cursor.close()

    def apply_new_clustering(self, new_clusters):
        """
        Применяет результаты новой кластеризации к базе данных.
        1. Удаляет старые группы.
        2. Сбрасывает group_id у ключевых слов.
        3. Создает новые группы и обновляет group_id у ключевых слов.
        """
        if LOGGING_ENABLED:
            logger.info(
                f"Применение новой кластеризации для проекта ID: {self.project_id}"
            )
        cursor = self.connection.cursor()

        try:
            # 1. Сбрасываем group_id у всех ключевых слов проекта
            cursor.execute(
                "UPDATE queries SET query_group_id = NULL WHERE project_id = %s",
                (self.project_id,),
            )
            if LOGGING_ENABLED:
                logger.info(
                    f"Сброшены group_id для ключевых слов проекта {self.project_id}."
                )

            # 2. Удаляем старые группы для данного проекта
            cursor.execute(
                "DELETE FROM query_groups WHERE project_id = %s", (self.project_id,)
            )
            if LOGGING_ENABLED:
                logger.info(f"Удалены старые группы для проекта {self.project_id}.")

            # 3. Создаем новые группы и обновляем ключи
            for cluster in new_clusters:
                main_keyword = cluster["main_keyword"]
                group_name = main_keyword["name"]

                # Создаем новую группу
                insert_group_query = (
                    "INSERT INTO query_groups (project_id, name) VALUES (%s, %s)"
                )
                cursor.execute(insert_group_query, (self.project_id, group_name))
                new_group_id = cursor.lastrowid

                # Собираем ID всех участников кластера
                member_ids = [member["id"] for member in cluster["members"]]

                # Обновляем group_id для всех участников
                # Используем форматирование для создания плейсхолдеров %s
                if member_ids:  # Проверяем, что список не пустой
                    placeholders = ", ".join(["%s"] * len(member_ids))
                    update_keywords_query = f"UPDATE queries SET query_group_id = %s WHERE id IN ({placeholders})"

                    params = [new_group_id] + member_ids
                    cursor.execute(update_keywords_query, params)

            self.connection.commit()
            if LOGGING_ENABLED:
                logger.info("Новая структура групп успешно применена.")

        except Exception as e:
            self.connection.rollback()
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка при применении новой кластеризации: {e}", exc_info=True
                )
            raise
        finally:
            cursor.close()
