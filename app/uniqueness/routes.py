from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
import os
import logging
import threading
import uuid
from flask_login import current_user
from .checker import UniquenessChecker
from ..db_config import LOGGING_ENABLED
from app.db.settings_db import get_setting
from app.db.uniqueness_db import (
    create_uniqueness_task,
    get_uniqueness_task,
    get_user_uniqueness_tasks,
    delete_uniqueness_task,
    reserve_user_limits,
    refund_user_limits,
    set_uniqueness_task_error,
)

logger = logging.getLogger(__name__)

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "uniqueness_routes.log")
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

uniqueness_bp = Blueprint("uniqueness", __name__)


@uniqueness_bp.route("/uniqueness")
@login_required
def uniqueness_page():
    """Отображает страницу проверки уникальности текста."""
    history = []
    if current_user.is_authenticated:
        history = get_user_uniqueness_tasks(current_user.id)
    return render_template("uniqueness.html", history=history)


@uniqueness_bp.route("/uniqueness/estimate", methods=["POST"])
@login_required
def estimate_uniqueness():
    """Рассчитывает стоимость проверки (количество шинглов)."""
    try:
        data = request.get_json()
        text_input = data.get("text_input", "").strip()

        if not text_input:
            return jsonify({"error": "Текст не указан"}), 400

        # Получаем настройки с защитой от некорректных значений
        shingle_len = int(get_setting("UNIQUENESS_SHINGLE_LENGTH") or 3)
        shingle_step = int(get_setting("UNIQUENESS_SHINGLE_STEP") or 3)
        sampling_mode = get_setting("UNIQUENESS_SAMPLING_MODE") or "deterministic"

        # Гарантируем, что значения не меньше 1
        shingle_len = max(1, shingle_len)
        shingle_step = max(1, shingle_step)

        # Считаем стоимость с учетом кеша
        checker = UniquenessChecker()
        estimate = checker.get_estimated_cost(
            text_input, shingle_len, shingle_step, sampling_mode=sampling_mode
        )
        cost = estimate["to_pay"]

        return jsonify(
            {
                "success": True,
                "cost": cost,
                "total_shingles": estimate["total"],
                "cached_shingles": estimate["cached"],
                "user_limits": current_user.limits,
                "can_afford": current_user.limits >= cost,
            }
        )
    except Exception as e:
        logger.error(f"Ошибка при расчете стоимости: {e}", exc_info=True)
        return jsonify({"error": "Ошибка при расчете стоимости"}), 500


@uniqueness_bp.route("/uniqueness/check", methods=["POST"])
# @login_required
def check_uniqueness():
    """Обрабатывает запрос на проверку уникальности."""
    try:
        data = request.get_json()
        text_input = data.get("text_input", "").strip()

        if not text_input:
            return jsonify({"error": "Текст не указан"}), 400

        if len(text_input) < 50:
            return (
                jsonify({"error": "Текст слишком короткий (минимум 50 символов)"}),
                400,
            )

        # Инициализируем чекер
        checker = UniquenessChecker()

        # Получаем опцию верификации контента
        verify_content = data.get("verify_content", False)

        # Запускаем проверку
        # Получаем настройки с защитой от некорректных значений
        shingle_len = int(get_setting("UNIQUENESS_SHINGLE_LENGTH") or 3)
        shingle_step = int(get_setting("UNIQUENESS_SHINGLE_STEP") or 3)
        sampling_mode = get_setting("UNIQUENESS_SAMPLING_MODE") or "deterministic"

        # Гарантируем, что значения не меньше 1 (защита от деления на 0 и бесконечных циклов)
        shingle_len = max(1, shingle_len)
        shingle_step = max(1, shingle_step)

        if LOGGING_ENABLED:
            logger.info(
                f"Запуск проверки: shingle_len={shingle_len}, shingle_step={shingle_step}"
            )

        # Создаем уникальный ID задачи
        task_id = str(uuid.uuid4())
        user_id = current_user.id if current_user.is_authenticated else None

        # Получаем данные о стоимости и кеше
        estimate = checker.get_estimated_cost(
            text_input, shingle_len, shingle_step, sampling_mode=sampling_mode
        )
        progress_total = estimate["total"]
        reserve_amount = estimate["to_pay"]

        # Сохраняем задачу в БД
        create_uniqueness_task(task_id, user_id, progress_total, source_text=text_input)

        # Резервируем лимиты (если пользователь авторизован)
        if user_id:
            if not reserve_user_limits(user_id, task_id, reserve_amount):
                from app.db.uniqueness_db import set_uniqueness_task_error

                set_uniqueness_task_error(task_id, "Недостаточно лимитов")
                return jsonify({"error": "Недостаточно лимитов"}), 402

        # Функция-обертка для фонового выполнения
        def run_check_background(tid, uid, txt, sl, ss, nt, vc, sm):
            try:
                checker.check_text_multithreaded(
                    txt,
                    shingle_len=sl,
                    stride=ss,
                    threads=nt,
                    verify_content=vc,
                    task_id=tid,
                    sampling_mode=sm,
                )
            except Exception as ex:
                logger.error(
                    f"Ошибка в фоновом потоке задачи {tid}: {ex}", exc_info=True
                )
                set_uniqueness_task_error(tid, str(ex))

        # Запускаем фоновый поток
        # Запуск выполнения в отдельном потоке
        thread = threading.Thread(
            target=run_check_background,
            args=(
                task_id,
                user_id,
                text_input,
                shingle_len,
                shingle_step,
                5,
                verify_content,
                sampling_mode,
            ),
        )
        thread.start()

        return jsonify({"success": True, "task_id": task_id})

    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при запуске проверки уникальности: {e}", exc_info=True
            )
        return (
            jsonify({"error": "Произошла ошибка при запуске проверки уникальности"}),
            500,
        )


@uniqueness_bp.route("/uniqueness/status/<task_id>", methods=["GET"])
# @login_required
def get_task_status(task_id):
    """Возвращает статус и результат (если готов) задачи."""
    try:
        task = get_uniqueness_task(task_id)
        if not task:
            return jsonify({"error": "Задача не найдена"}), 404

        response = {
            "status": task["status"],
            "progress_current": task["progress_current"],
            "progress_total": task["progress_total"],
            "source_text": task.get("source_text"),
        }

        if task["status"] == "completed":
            response["result"] = task["result"]
        elif task["status"] == "error":
            response["error"] = task["error_message"]

        return jsonify(response)

    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(
                f"Ошибка при получении статуса задачи {task_id}: {e}", exc_info=True
            )
        return jsonify({"error": "Произошла ошибка при получении статуса задачи"}), 500


@uniqueness_bp.route("/uniqueness/delete/<task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id):
    """Удаляет задачу из истории."""
    try:
        success = delete_uniqueness_task(task_id, current_user.id)
        if success:
            return jsonify({"success": True, "message": "Задача удалена"})
        else:
            return jsonify({"error": "Задача не найдена или доступ запрещен"}), 404
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(f"Ошибка при удалении задачи {task_id}: {e}", exc_info=True)
        return jsonify({"error": "Ошибка при удалении задачи"}), 500
