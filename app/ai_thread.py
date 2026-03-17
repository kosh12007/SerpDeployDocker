import threading
import logging
import os
import asyncio
from .db.ai_db import update_ai_task_status, save_ai_result
from .ai import DeepSeekService
from .config import DEEPSEEK_API_KEY
from app.db_config import LOGGING_ENABLED
from app.config import Config

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "ai_thread.log")
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
# --- Конец настройки логгера ---

ai_analysis_status = {}


def run_ai_task(task_id, system_prompt, user_message):
    """
    Основная функция воркера для выполнения AI-задачи.
    """
    if LOGGING_ENABLED:
        logger.info(f"Начало выполнения AI-задачи {task_id}")
    ai_analysis_status[task_id] = {
        "status": "running",
        "progress": 10,
        "message": "Задача в обработке",
    }

    try:
        # Обновляем статус задачи на 'running'
        update_ai_task_status(task_id, "running")

        ai_analysis_status[task_id]["progress"] = 30

        # Запускаем асинхронную операцию
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ai_response = loop.run_until_complete(
            process_message(system_prompt, user_message)
        )
        loop.close()

        ai_analysis_status[task_id]["progress"] = 80

        # Сохраняем результат
        if LOGGING_ENABLED:
            logger.info(
                f"AI response received for task {task_id}. Type: {type(ai_response)}. Length: {len(str(ai_response))} chars."
            )
            logger.info(f"Response preview: {str(ai_response)[:200]}...")

        save_ai_result(task_id, user_message, ai_response)

        # Обновляем статус задачи на 'completed'
        update_ai_task_status(task_id, "completed")

        ai_analysis_status[task_id] = {
            "status": "completed",
            "progress": 100,
            "message": "Задача выполнена",
        }
        if LOGGING_ENABLED:
            logger.info(f"AI-задача {task_id} успешно выполнена и сохранена.")

    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при выполнении AI-задачи {task_id}: {e}", exc_info=True
            )
        update_ai_task_status(task_id, "error")
        ai_analysis_status[task_id] = {
            "status": "error",
            "progress": 100,
            "message": f"Ошибка: {e}",
        }


async def process_message(system_prompt, user_message):
    """
    Асинхронно отправляет запрос к AI.
    """
    if not DEEPSEEK_API_KEY:
        raise ValueError("API-ключ для DeepSeek не настроен.")

    service = DeepSeekService(token=DEEPSEEK_API_KEY)
    response = await service.send_question(
        prompt_text=system_prompt, message_text=user_message
    )
    return response


def start_ai_analysis(task_id, system_prompt, user_message):
    """
    Запускает выполнение AI-задачи в отдельном потоке.
    """
    thread = threading.Thread(
        target=run_ai_task, args=(task_id, system_prompt, user_message)
    )
    thread.start()
    return thread
