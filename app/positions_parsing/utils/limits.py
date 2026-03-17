# -*- coding: utf-8 -*-
import os
import logging
from app.models import ParsingVariant, Query, User
from app.db.database import get_db_connection
from app.db_config import LOGGING_ENABLED

# --- Настройка логгера ---
if LOGGING_ENABLED:
    # Используем относительные пути для большей переносимости
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "limits_positions_parsing.log")

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


def check_limits_and_calculate_cost(
    user_id: int,
    project_id: int,
    queries_count: int,
    search_engine_id: int,
    depth: int,
    search_type: str,
) -> int:
    """
    Проверяет, достаточно ли у пользователя лимитов для выполнения парсинга, и рассчитывает стоимость.
    Работает в одном режиме с полной информацией: user_id, project_id, queries_count, search_engine_id, depth, search_type

    Args:
        user_id: ID пользователя
        project_id: ID проекта
        queries_count: Количество запросов
        search_engine_id: ID поисковой системы
        depth: Глубина парсинга (количество страниц)
        search_type: Тип поиска (например, 'live_search' или 'search_api')

    Returns:
        Рассчитанная стоимость операции в виде целого числа

    Raises:
        ValueError: Если у пользователя недостаточно лимитов
    """
    # Основной режим с полной информацией
    cost = calculate_cost(queries_count, search_engine_id, depth, search_type)

    # Если указан ID пользователя, проверяем лимиты
    if user_id is not None:
        if not has_sufficient_limits(user_id, cost):
            available_limits = get_available_limits(user_id)
            raise ValueError(
                f"Недостаточно лимитов для выполнения операции. Требуется: {cost}, доступно: {available_limits}"
            )

    return cost


def calculate_cost(
    queries_count: int, search_engine_id: int, depth: int, search_type: str
) -> int:
    """
    Рассчитывает стоимость парсинга на основе переданных параметров.

    Args:
        queries_count: Количество запросов
        search_engine_id: ID поисковой системы
        depth: Глубина парсинга (количество страниц)
        search_type: Тип поиска ('live_search' или 'search_api')

    Returns:
        Рассчитанная стоимость операции
    """
    # Проверяем типы параметров и конвертируем их, если необходимо
    try:
        # Проверяем, является ли queries_count числом или строкой, которую можно преобразовать в число
        if isinstance(queries_count, str):
            queries_count = int(queries_count)
        elif not isinstance(queries_count, int):
            queries_count = int(queries_count)
    except (ValueError, TypeError):
        logger.error(
            f"Невозможно преобразовать queries_count в целое число: {queries_count}"
        )
        queries_count = 1  # Устанавливаем значение по умолчанию

    try:
        # Проверяем, является ли depth числом или строкой, которую можно преобразовать в число
        if isinstance(depth, str):
            depth = int(depth)
        elif not isinstance(depth, int):
            depth = int(depth)
    except (ValueError, TypeError):
        logger.error(f"Невозможно преобразовать depth в целое число: {depth}")
        depth = 1  # Устанавливаем значение по умолчанию

    # Проверяем, является ли search_engine_id числом или строкой, которую можно преобразовать в число
    try:
        if isinstance(search_engine_id, str):
            search_engine_id = int(search_engine_id)
    except (ValueError, TypeError):
        logger.error(
            f"Невозможно преобразовать search_engine_id в целое число: {search_engine_id}"
        )
        search_engine_id = 1  # Устанавливаем значение по умолчанию

    # Базовая стоимость зависит от поисковой системы и типа поиска
    from app.models import SearchEngine

    search_engine = SearchEngine.get_by_id(search_engine_id)

    if LOGGING_ENABLED:
        logger.info(
            f"Расчет стоимости для: queries_count={queries_count}, search_engine_id={search_engine_id}, depth={depth}, search_type='{search_type}'"
        )

    cost = 0
    if search_engine and search_engine.api_name.lower() == "yandex":
        if search_type == "search_api":
            # Яндекс, API: Стоимость = queries_count
            cost = queries_count
            if LOGGING_ENABLED:
                logger.info(f"Расчет для Яндекс (API): cost = {queries_count}")
        else:
            # Яндекс, живой поиск: Стоимость = queries_count * depth
            cost = queries_count * depth
            if LOGGING_ENABLED:
                logger.info(
                    f"Расчет для Яндекс (живой поиск): cost = {queries_count} * {depth} = {cost}"
                )
    else:
        # Google или другая ПС: Стоимость = queries_count * depth
        cost = queries_count * depth
        if LOGGING_ENABLED:
            se_name = search_engine.api_name if search_engine else "Неизвестная ПС"
            logger.info(
                f"Расчет для {se_name}: cost = {queries_count} * {depth} = {cost}"
            )

    if LOGGING_ENABLED:
        logger.info(f"Итоговая стоимость: {cost}")

    return cost


def has_sufficient_limits(user_id: int, required_cost: int) -> bool:
    """
    Проверяет, достаточно ли лимитов у пользователя для выполнения операции.

    Args:
        user_id: ID пользователя
        required_cost: Требуемая стоимость операции

    Returns:
        True, если лимитов достаточно, иначе False
    """
    available_limits = get_available_limits(user_id)
    return available_limits >= required_cost


def get_available_limits(user_id: int) -> int:
    """
    Получает доступное количество лимитов для пользователя.

    Args:
        user_id: ID пользователя

    Returns:
        Количество доступных лимитов
    """
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("SELECT limits FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            cursor.close()
            connection.close()

            if result:
                total_limits = result[0]
                return total_limits
            else:
                raise ValueError(f"Пользователь с ID {user_id} не найден.")
    except Exception as e:
        logger.error(
            f"Ошибка при получении доступных лимитов для пользователя {user_id}: {e}",
            exc_info=True,
        )
        raise


def estimate_limits(variant_id: int, project_id: int) -> tuple[int, int]:
    """
    Рассчитывает предполагаемую стоимость парсинга на основе варианта и запросов проекта.

    Args:
        variant_id: ID варианта парсинга.
        project_id: ID проекта.

    Returns:
        Кортеж, содержащий предполагаемую стоимость (estimated_cost) и количество запросов (queries_count).
        Возвращает (0, 0), если вариант парсинга не найден.
    """
    # 1. Получаем вариант парсинга
    variant = ParsingVariant.get_by_id(variant_id)
    if LOGGING_ENABLED:
        logger.info(
            f"Выводим всё что получили по вариант id '{variant.search_engine_api_name} {variant.api_parameter}' "
        )
    if not variant:
        return 0, 0

    # 2. Получаем все запросы для проекта
    queries = Query.get_by_project_id(project_id)
    queries_count = len(queries)

    # 3. Рассчитываем предполагаемую стоимость

    if (
        variant.search_engine_api_name.lower() == "yandex"
        and variant.api_parameter == "api"
    ):
        estimated_cost = queries_count
        if LOGGING_ENABLED:
            logger.info(
                f"Предварительный расчет для Яндекс (API) '{variant.search_engine_api_name} {variant.api_parameter}': estimated_cost = {queries_count}"
            )
    else:  # Live Search или Google
        page_limit = variant.page_limit if variant.page_limit else 10
        estimated_cost = queries_count * page_limit
        if LOGGING_ENABLED:
            logger.info(
                f"Предварительный расчет для '{variant.search_engine_api_name} {variant.api_parameter}' (живой поиск): estimated_cost = {queries_count} * {page_limit} = {estimated_cost}"
            )

    return estimated_cost, queries_count
