import threading
import time
from .page_analyzer import extract_page_data
from .db.page_analyzer_db import save_page_analysis_result
from .db.database import create_connection
import logging
import os

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "page_analyzer_thread.log")
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
logger.info(f"Логгер для {__name__} настроен.")
# --- Конец настройки логгера ---

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
        "total": total_urls,
        "completed": 0,
        "status": "running",
    }

    logger.info(f"Запуск анализа для task_id={task_id} с {total_urls} URL.")
    for url in urls:
        clean_url = url.strip()
        if not clean_url:
            logger.warning(f"Пропущен пустой URL в task_id={task_id}")
            continue
        try:
            logger.debug(f"Анализ URL: {clean_url} для task_id={task_id}")
            # Здесь должен быть ваш код для анализа страницы
            analysis_results = extract_page_data(clean_url)
            if "error" not in analysis_results:
                save_page_analysis_result(task_id, clean_url, analysis_results)
                logger.debug(
                    f"Результаты для {clean_url} (task_id={task_id}) успешно сохранены."
                )
            else:
                logger.warning(
                    f"Анализ {clean_url} (task_id={task_id}) вернул ошибку: {analysis_results.get('error')}"
                )
        except Exception as e:
            # Логирование ошибок
            logger.error(
                f"Критическая ошибка при анализе {clean_url} (task_id={task_id}): {e}",
                exc_info=True,
            )
        finally:
            completed_count += 1
            analysis_status[task_id]["completed"] = completed_count
            analysis_status[task_id]["progress"] = (completed_count / total_urls) * 100

    analysis_status[task_id]["status"] = "completed"
    logger.info(f"Анализ для task_id={task_id} завершен.")

    # Обновляем статус задачи в БД
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE page_analysis_tasks SET status = 'completed' WHERE id = %s",
                (task_id,),
            )
            connection.commit()
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса задачи {task_id} в БД: {e}")
        finally:
            cursor.close()
            connection.close()


def start_analysis(task_id, urls):
    """Запускает анализ в фоновом потоке."""
    thread = threading.Thread(target=run_page_analysis_thread, args=(task_id, urls))
    thread.start()
    return thread
