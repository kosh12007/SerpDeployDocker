import threading
import time
from .page_analyzer import extract_page_data
from .db.page_analyzer_db import save_page_analysis_result
from .db.database import create_connection

# Глобальный словарь для отслеживания состояния задач
analysis_status = {}

def run_page_analysis_thread(task_id, urls):
    """
    Выполняется в отдельном потоке. Итерируется по списку URL,
    вызывает анализатор и сохраняет результаты.
    """
    total_urls = len(urls)
    completed_count = 0

    analysis_status[task_id] = {
        'total': total_urls,
        'completed': 0,
        'status': 'running'
    }

    for url in urls:
        try:
            # Здесь должен быть ваш код для анализа страницы
            analysis_results = extract_page_data(url)
            if "error" not in analysis_results:
                save_page_analysis_result(task_id, url, analysis_results)
        except Exception as e:
            # Логирование ошибок
            print(f"Ошибка при анализе {url}: {e}")
        finally:
            completed_count += 1
            analysis_status[task_id]['completed'] = completed_count
            analysis_status[task_id]['progress'] = (completed_count / total_urls) * 100

    analysis_status[task_id]['status'] = 'completed'

    # Обновляем статус задачи в БД
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("UPDATE page_analysis_tasks SET status = 'completed' WHERE id = %s", (task_id,))
            connection.commit()
        except Exception as e:
            print(f"Ошибка при обновлении статуса задачи {task_id}: {e}")
        finally:
            cursor.close()
            connection.close()

def start_analysis(task_id, urls):
    """Запускает анализ в фоновом потоке."""
    thread = threading.Thread(target=run_page_analysis_thread, args=(task_id, urls))
    thread.start()
    return thread