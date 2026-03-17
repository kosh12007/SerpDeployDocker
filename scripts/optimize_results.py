import sys
import os
import json

# ==================================================================================
# СКРИПТ ОПТИМИЗАЦИИ ИСТОРИИ ПРОВЕРОК УНИКАЛЬНОСТИ
# ==================================================================================
# Назначение:
# 1. Очистка базы данных от "мусорных" URL в старых задачах.
# 2. Добавление поля 'top_urls' в старые задачи для мгновенной загрузки в интерфейсе.
# 3. Уменьшение объема JSON в таблице uniqueness_tasks.
#
# Как использовать:
# Запустите из корня проекта: python optimize_results.py
# ==================================================================================

# Добавляем корневую директорию проекта в sys.path, чтобы импортировать модули app
sys.path.append(os.getcwd())

from app import application
from app.db.database import create_connection
from app.db.settings_db import get_setting


def optimize_history():
    # Работаем внутри контекста приложения Flask для доступа к настройкам и БД
    with application.app_context():
        print("🚀 Запуск оптимизации истории результатов...")

        # --- НАСТРОЙКИ ---
        # Вы можете раскомментировать строки ниже, чтобы задать жесткие лимиты вручную
        # вместо того, чтобы брать их из общей таблицы настроек.

        # manual_min_percent = 5  # Например, оставить только выше 5% совпадений
        # manual_max_urls = 50    # Например, оставить только ТОП-50 адресов

        try:
            min_percent = int(get_setting("UNIQUENESS_MIN_MATCH_PERCENT") or 2)
            max_urls = int(get_setting("UNIQUENESS_MAX_MATCH_URLS") or 100)

            # Если заданы ручные переопределения выше:
            # min_percent = manual_min_percent
            # max_urls = manual_max_urls
        except:
            min_percent = 2
            max_urls = 100

        print(
            f"⚙️ Используемые параметры: мин % совпадения = {min_percent}, макс URL в отчете = {max_urls}"
        )

        # Устанавливаем соединение с базой данных
        conn = create_connection()
        if not conn:
            print("❌ Ошибка: Не удалось подключиться к базе данных.")
            return

        try:
            cur = conn.cursor(dictionary=True)

            # Выбираем все задачи, у которых заполнен результат (JSON)
            cur.execute(
                "SELECT task_id, result FROM uniqueness_tasks WHERE result IS NOT NULL"
            )
            tasks = cur.fetchall()

            print(f"🔍 Найдено задач для обработки: {len(tasks)}")

            updated_count = 0
            for task in tasks:
                try:
                    task_id = task["task_id"]
                    if not task["result"]:
                        continue

                    # Десериализуем JSON результат задачи
                    data = json.loads(task["result"])
                    matches = data.get("matches", [])

                    # Пытаемся найти общее кол-во проверенных шинглов для расчета процента
                    total_attempted = (
                        data.get("attempted_shingles")
                        or data.get("checked_shingles")
                        or 1
                    )

                    if not matches:
                        continue

                    # 1. ШАГ: Собираем общую статистику по всем URL в этой задаче
                    url_stats = {}
                    for m in matches:
                        for u in m.get("urls", []):
                            url_stats[u] = url_stats.get(u, 0) + 1

                    # 2. ШАГ: Фильтруем URL по минимальному порогу совпадения
                    valid_urls_list = []
                    for url, count in url_stats.items():
                        # Процент совпадения = (сколько раз встретился URL / сколько всего фраз проверено) * 100
                        p = (count / total_attempted) * 100
                        if p >= min_percent:
                            valid_urls_list.append(
                                {"url": url, "count": count, "percent": round(p, 2)}
                            )

                    # 3. ШАГ: Сортируем список по убыванию совпадений и обрезаем по лимиту (например, ТОП-100)
                    valid_urls_list.sort(key=lambda x: x["count"], reverse=True)
                    valid_urls_list = valid_urls_list[:max_urls]

                    # Множество разрешенных URL для быстрой проверки при очистке
                    allowed_urls = {item["url"] for item in valid_urls_list}

                    # 4. ШАГ: Очищаем детальные совпадения (matches) от отфильтрованных URL
                    optimized_matches = []
                    for m in matches:
                        # Оставляем только те URL, которые прошли фильтр ТОП-а
                        m["urls"] = [u for u in m.get("urls", []) if u in allowed_urls]
                        # Если после фильтрации у фразы остались совпадения, сохраняем её
                        if m["urls"]:
                            optimized_matches.append(m)

                    # 5. ШАГ: Обновляем структуру JSON
                    data["matches"] = optimized_matches  # Облегченный список совпадений
                    data["top_urls"] = (
                        valid_urls_list  # Готовый список для легенды в UI
                    )

                    # Сериализуем обратно в JSON
                    new_result_json = json.dumps(data, ensure_ascii=False)

                    # Сохраняем обновленный результат в БД
                    cur.execute(
                        "UPDATE uniqueness_tasks SET result = %s WHERE task_id = %s",
                        (new_result_json, task_id),
                    )
                    updated_count += 1

                    # Выводим прогресс каждые 50 записей
                    if updated_count % 50 == 0:
                        print(f"✅ Успешно обработано {updated_count} записей...")

                except Exception as e:
                    print(f"⚠️ Ошибка при обработке задачи {task.get('task_id')}: {e}")
                    continue

            # Фиксируем изменения в базе данных
            conn.commit()
            print(f"\n✨ Оптимизация завершена успешно!")
            print(f"📊 Итого обновлено задач: {updated_count}")

        except Exception as ex:
            print(f"🚨 Критическая ошибка при работе с БД: {ex}")
        finally:
            cur.close()
            conn.close()


if __name__ == "__main__":
    # Запуск скрипта
    try:
        optimize_history()
    except KeyboardInterrupt:
        print("\n🛑 Процесс прерван пользователем.")
    except Exception as e:
        print(f"\n❌ Произошла ошибка: {e}")
