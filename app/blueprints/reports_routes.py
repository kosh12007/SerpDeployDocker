# app/blueprints/reports_routes.py

from flask import Blueprint, request, jsonify
from app import cache
from app.db.database import create_connection
from app.parsing_utils import get_top_competitors
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание Blueprint для отчетов
reports_bp = Blueprint('reports_bp', __name__)

@reports_bp.route('/position-dynamics', methods=['GET'])
@cache.cached(query_string=True)
def get_position_dynamics():
    """
    Возвращает динамику позиций для заданного запроса и варианта.
    Параметры:
        query_id (int): ID поискового запроса.
        parsing_variant_id (int): ID варианта парсинга.
    Возвращает:
        JSON: Список словарей с датой и позицией.
    """
    query_id = request.args.get('query_id')
    parsing_variant_id = request.args.get('parsing_variant_id')

    if not query_id or not parsing_variant_id:
        return jsonify({"error": "Необходимо указать query_id и parsing_variant_id"}), 400

    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # Проверка существования запроса
        cursor.execute("SELECT id FROM queries WHERE id = %s", (query_id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Запрос с ID {query_id} не найден"}), 404
        
        # Проверка существования варианта
        cursor.execute("SELECT id FROM parsing_variants WHERE id = %s", (parsing_variant_id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Вариант с ID {parsing_variant_id} не найден"}), 404

        # Получение результатов из БД
        sql_query = """
            SELECT date, position
            FROM parsing_position_results
            WHERE query_id = %s AND parsing_variant_id = %s
            ORDER BY date
        """
        cursor.execute(sql_query, (query_id, parsing_variant_id))
        results = cursor.fetchall()

        # Формирование ответа
        position_dynamics = [
            {'date': result['date'].isoformat(), 'position': result['position']}
            for result in results
        ]

        return jsonify(position_dynamics)

    except Exception as e:
        logger.error(f"Ошибка при получении динамики позиций: {e}")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@reports_bp.route('/top-competitors', methods=['GET'])
@cache.cached(query_string=True)
def top_competitors_report():
    """
    Возвращает топ конкурентов для проекта по варианту и дате.
    Параметры:
        project_id (int): ID проекта.
        variant_id (int): ID варианта парсинга.
        date (str): Дата в формате YYYY-MM-DD.
    Возвращает:
        JSON: Список кортежей [('domain', count), ...].
    """
    project_id = request.args.get('project_id')
    variant_id = request.args.get('variant_id')
    date = request.args.get('date')

    if not all([project_id, variant_id, date]):
        return jsonify({"error": "Необходимо указать project_id, variant_id и date"}), 400
        
    # Проверка существования проекта
    connection = create_connection()
    if not connection:
        return jsonify({"error": "Не удалось подключиться к базе данных."}), 500
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM projects WHERE id = %s", (project_id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Проект с ID {project_id} не найден"}), 404
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    try:
        # Получение данных с помощью вспомогательной функции
        competitors = get_top_competitors(
            project_id=int(project_id), 
            variant_id=int(variant_id), 
            date=date
        )
        return jsonify(competitors)
    except Exception as e:
        # Обработка возможных ошибок из get_top_competitors
        return jsonify({"error": str(e)}), 500
