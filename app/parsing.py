import subprocess
import os
import logging
import threading
import time
import datetime
import uuid
import re
from .db.database import (
    create_connection,
    update_session_status,
    get_results_from_db,
    spend_limit,
    update_session_spent_limits,
)
from .models import User
from .config import MODE
from .xmlriver_client import (
    get_api_credentials,
    get_position_and_url_single_page,
    get_live_search_position_looped,
    get_google_position_looped,
)
from mysql.connector import Error

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "parsing.log")
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

# Глобальные переменные для отслеживания состояния парсинга
parsing_status = {
    "is_running": False,
    "progress": 0,
    "current_query": "",
    "total_queries": 0,
    "completed_queries": 0,
    "results": [],
    "error": None,
}


def run_parsing_in_thread(
    engine,
    queries,
    domain,
    mode,
    session_id,
    user_id,
    yandex_type="search_api",
    yandex_page_limit=9,
    google_page_limit=10,
    loc_id=213,
):
    """Функция для запуска парсинга в отдельном потоке"""
    global parsing_status
    logger.info(
        f"Запуск потока парсинга для сессии {session_id} с параметрами: engine={engine}, domain={domain}, yandex_type={yandex_type}, yandex_page_limit={yandex_page_limit}, google_page_limit={google_page_limit}, loc_id={loc_id}, user_id={user_id}"
    )

    spent_limits = 0

    try:
        user = User.get_by_id(user_id)
        if not user:
            parsing_status["error"] = f"Пользователь {user_id} не найден."
            update_session_status(session_id, "error")
            logger.error(f"Пользователь {user_id} не найден для сессии {session_id}.")
            return

        parsing_status["is_running"] = True
        parsing_status["progress"] = 0
        parsing_status["error"] = None
        parsing_status["results"] = []

        queries_lines = [line.strip() for line in queries.split("\n") if line.strip()]
        from app.db.settings_db import get_setting

        max_queries = int(get_setting("MAX_QUERIES") or 5)
        if len(queries_lines) > max_queries:
            queries_lines = queries_lines[:max_queries]

        # Расчет необходимого количества лимитов
        queries_count = len(queries_lines)
        if engine == "yandex" and yandex_type == "search_api":
            required_limits = queries_count
        else:  # Live Search или Google
            page_limit = (
                int(google_page_limit) if engine == "google" else int(yandex_page_limit)
            )
            required_limits = queries_count * page_limit

        # Проверка лимитов пользователя
        try:
            user_limits = int(user.limits) if user.limits is not None else 0
        except (ValueError, TypeError):
            logger.error(
                f"Невозможно преобразовать лимиты пользователя в число: {user.limits}"
            )
            parsing_status["error"] = (
                "Ошибка внутренней логики: неверный формат лимитов пользователя."
            )
            update_session_status(session_id, "error")
            return

        if user_limits < required_limits:
            parsing_status["error"] = (
                f"Недостаточно лимитов. Требуется: {required_limits}, доступно: {user_limits}"
            )
            update_session_status(session_id, "error")
            logger.error(parsing_status["error"])
            return

        # Убираем предварительное списание лимитов. Списание будет после выполнения main.py.
        # if not spend_limit(user_id, required_limits):
        #     parsing_status['error'] = "Ошибка при списании лимитов."
        #     update_session_status(session_id, 'error')
        #     logger.error(f"Не удалось списать {required_limits} лимитов для пользователя {user_id}.")
        #     return

        # spent_limits = required_limits
        # update_session_spent_limits(session_id, spent_limits)

        with open("temp_queries.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(queries_lines))

        if mode == "hosting":
            python_path = "/var/www/u0669189/data/serp/bin/python"
        else:
            python_path = "python"

        parsing_status["progress"] = 10

        env = os.environ.copy()
        env["SESSION_ID"] = session_id
        env["YANDEX_TYPE"] = yandex_type
        # Явно устанавливаем переменную окружения для дочернего процесса
        if os.getenv("OPENBLAS_NUM_THREADS"):
            env["OPENBLAS_NUM_THREADS"] = os.getenv("OPENBLAS_NUM_THREADS")

        # Получаем количество потоков из настроек БД
        threads_count = int(get_setting("UNIQUENESS_THREADS") or 5)
        logger.info(f"Количество потоков для парсинга из настроек: {threads_count}")

        cmd = [
            python_path,
            "main.py",
            engine,
            "temp_queries.txt",
            domain,
            yandex_type,
            str(yandex_page_limit),
            str(google_page_limit),
            str(loc_id),
            "--threads",
            str(threads_count),
        ]
        cmd = [arg for arg in cmd if arg is not None]
        logger.info(f"Выполнение команды: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            env=env,
        )

        logger.info(f"Команда завершена. STDOUT: {result.stdout}")
        logger.error(f"Команда завершена. STDERR: {result.stderr}")

        # Извлекаем количество использованных лимитов из STDOUT
        actual_spent_limits = None
        used_limits_match = re.search(
            r"=== ИТОГО ИСПОЛЬЗОВАНО ЛИМИТОВ: (\d+) ===", result.stdout
        )
        if used_limits_match:
            actual_spent_limits = int(used_limits_match.group(1))
            logger.info(
                f"Извлечено количество использованных лимитов из main.py: {actual_spent_limits}"
            )

            # Проверяем, достаточно ли лимитов у пользователя для списания
            if int(user.limits) < actual_spent_limits:
                parsing_status["error"] = (
                    f"Недостаточно лимитов для списания после выполнения. Требуется: {actual_spent_limits}, доступно: {user.limits}"
                )
                update_session_status(session_id, "error")
                logger.error(parsing_status["error"])
                return

            # Списываем лимиты
            if not spend_limit(user_id, actual_spent_limits):
                parsing_status["error"] = (
                    "Ошибка при списании лимитов после выполнения."
                )
                update_session_status(session_id, "error")
                logger.error(
                    f"Не удалось списать {actual_spent_limits} лимитов для пользователя {user_id} после выполнения."
                )
                return

            logger.info(
                f"Списано {actual_spent_limits} лимитов после выполнения main.py."
            )
        else:
            logger.warning(
                "Количество использованных лимитов не найдено в выводе main.py. Используем расчетное значение."
            )
            # Если не удалось извлечь, используем расчетное количество для списания и обновления сессии
            if not spend_limit(user_id, required_limits):
                parsing_status["error"] = "Ошибка при списании расчетных лимитов."
                update_session_status(session_id, "error")
                logger.error(
                    f"Не удалось списать расчетные {required_limits} лимитов для пользователя {user_id}."
                )
                return

            actual_spent_limits = required_limits
            logger.info(f"Списано расчетное количество лимитов: {required_limits}")

        # Обновляем количество потраченных лимитов в сессии в любом случае
        if actual_spent_limits is not None:
            logger.info(
                f"Попытка обновить поле spent_limits в сессии {session_id} на значение {actual_spent_limits}."
            )
            update_session_spent_limits(session_id, actual_spent_limits)
            logger.info(
                f"Поле spent_limits в сессии {session_id} обновлено на значение {actual_spent_limits}."
            )
        else:
            logger.error(
                f"Не удалось определить количество потраченных лимитов для сессии {session_id}."
            )

        parsing_status["progress"] = 80

        try:
            os.remove("temp_queries.txt")
        except FileNotFoundError:
            pass

        parsing_status["progress"] = 85

        results = get_results_from_db(session_id)
        logger.info(
            f"Получено {len(results)} результатов из базы данных для сессии {session_id}"
        )

        if not results:
            parsing_status["error"] = "Результаты не были получены из базы данных"
            logger.error(
                f"Результаты не были получены из базы данных для сессии {session_id}"
            )
            parsing_status["results"] = []
            parsing_status["progress"] = 10
            update_session_status(session_id, "error")
        else:
            try:
                parsing_status["progress"] = 90

                positions = [
                    int(r["position"])
                    for r in results
                    if r["position"] and r["position"] != "-"
                ]
                if positions:
                    avg_position = sum(positions) / len(positions)
                    top_10 = len([p for p in positions if p <= 10])
                else:
                    avg_position = 0
                    top_10 = 0

                parsing_status["results"] = results
                parsing_status["avg_position"] = avg_position
                parsing_status["top_10"] = top_10
                parsing_status["progress"] = 100
                update_session_status(session_id, "completed")

            except Exception as e:
                parsing_status["error"] = f"Ошибка обработки результатов: {str(e)}"
                parsing_status["results"] = []
                parsing_status["progress"] = 10
                update_session_status(session_id, "error")

    except subprocess.TimeoutExpired:
        logger.error(
            f"Процесс парсинга для сессии {session_id} занял слишком много времени и был прерван."
        )
        parsing_status["error"] = (
            "Процесс парсинга занял слишком много времени и был прерван"
        )
        try:
            os.remove("temp_queries.txt")
        except FileNotFoundError:
            pass
        update_session_status(session_id, "error")
    except Exception as e:
        logger.error(
            f"Ошибка выполнения в потоке парсинга для сессии {session_id}: {str(e)}",
            exc_info=True,
        )
        parsing_status["error"] = f"Ошибка выполнения: {str(e)}"
        try:
            os.remove("temp_queries.txt")
        except FileNotFoundError:
            pass
        update_session_status(session_id, "error")
    finally:
        parsing_status["is_running"] = False
        logger.info(f"Поток парсинга для сессии {session_id} завершен.")


# Функция run_top_sites_parsing_thread перенесена в app/top_sites_parser_thread.py
# Импортируем её для обратной совместимости
from .top_sites_parser_thread import run_top_sites_parsing_thread
