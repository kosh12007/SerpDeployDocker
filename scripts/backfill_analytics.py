# -*- coding: utf-8 -*-
"""
Временный скрипт для заполнения таблицы uniqueness_analytics и uniqueness_source_domains
данными из существующих завершённых задач (uniqueness_tasks).

Извлекает метрики и список доменов из JSON-поля `result` каждой завершённой задачи.

Запуск: python scripts/backfill_analytics.py
"""

import sys
import os
import json
from urllib.parse import urlparse

# Добавляем корень проекта в пути, чтобы импорты работали
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import create_connection


def backfill_analytics():
    """
    Переносит данные из uniqueness_tasks (completed) в аналитические таблицы.
    Использует INSERT IGNORE для идемпотентности.
    """
    connection = create_connection()
    if not connection:
        print("❌ Не удалось подключиться к базе данных")
        return

    try:
        cursor = connection.cursor(dictionary=True)

        # Получаем все завершённые задачи с результатами
        cursor.execute(
            """
            SELECT task_id, user_id, result, progress_total, reserved_limits, created_at
            FROM uniqueness_tasks
            WHERE status = 'completed' AND result IS NOT NULL
        """
        )
        tasks = cursor.fetchall()

        if not tasks:
            print("⚠️ Нет завершённых задач для переноса")
            return

        print(f"📊 Найдено {len(tasks)} завершённых задач для переноса")

        inserted_main = 0
        inserted_domains = 0
        skipped = 0
        errors = 0

        for task in tasks:
            try:
                # Парсим JSON результата
                result = (
                    json.loads(task["result"])
                    if isinstance(task["result"], str)
                    else task["result"]
                )

                # 1. Метрики для основной таблицы аналитики
                score = result.get("score", 0)
                total_shingles = result.get(
                    "total_shingles", task["progress_total"] or 0
                )
                checked_shingles = result.get(
                    "checked_shingles", result.get("attempted_shingles", 0)
                )
                non_unique_shingles = result.get("non_unique_shingles", 0)
                cache_hits = result.get("cache_hits", 0)
                api_calls = result.get("api_calls", 0)
                text_length = result.get("text_length", 0)

                # Дорасчет для старых задач
                if cache_hits == 0 and api_calls == 0 and checked_shingles > 0:
                    api_calls = task["reserved_limits"] or 0
                    cache_hits = max(0, checked_shingles - api_calls)

                limits_spent = task["reserved_limits"] or 0

                # Вставляем основную запись
                cursor.execute(
                    """
                    INSERT IGNORE INTO uniqueness_analytics
                        (task_id, user_id, score, total_shingles, checked_shingles,
                         non_unique_shingles, cache_hits, api_calls, limits_spent, text_length, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        task["task_id"],
                        task["user_id"],
                        score,
                        total_shingles,
                        checked_shingles,
                        non_unique_shingles,
                        cache_hits,
                        api_calls,
                        limits_spent,
                        text_length,
                        task["created_at"],
                    ),
                )

                main_added = cursor.rowcount > 0
                if main_added:
                    inserted_main += 1
                else:
                    skipped += 1

                # 2. Метрики доменов-источников
                # В старых задачах это поле может называться top_urls
                top_urls = result.get("top_urls", [])
                if top_urls:
                    # Сначала проверим, нет ли уже записей для этой задачи в таблице доменов
                    cursor.execute(
                        "SELECT id FROM uniqueness_source_domains WHERE task_id = %s LIMIT 1",
                        (task["task_id"],),
                    )
                    if not cursor.fetchone():
                        domain_batch = []
                        for item in top_urls:
                            url = item.get("url", "")
                            if not url:
                                continue

                            domain = (
                                urlparse(url).netloc if url.startswith("http") else url
                            )
                            if domain:
                                domain_batch.append(
                                    (
                                        task["task_id"],
                                        domain,
                                        item.get("count", 0),
                                        task["created_at"],
                                    )
                                )

                        if domain_batch:
                            cursor.executemany(
                                """
                                INSERT INTO uniqueness_source_domains (task_id, domain, match_count, created_at)
                                VALUES (%s, %s, %s, %s)
                            """,
                                domain_batch,
                            )
                            inserted_domains += len(domain_batch)

                if main_added:
                    print(f"  ✅ {task['task_id']} перенесена")

            except Exception as e:
                errors += 1
                print(f"  ❌ Ошибка для задачи {task['task_id']}: {e}")
                continue

        connection.commit()

        print(f"\n{'='*50}")
        print(f"📈 Результат переноса:")
        print(f"   Записей аналитики: {inserted_main}")
        print(f"   Записей доменов: {inserted_domains}")
        print(f"   Пропущено (уже были): {skipped}")
        print(f"   Ошибки: {errors}")
        print(f"{'='*50}")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        connection.rollback()
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


if __name__ == "__main__":
    backfill_analytics()
