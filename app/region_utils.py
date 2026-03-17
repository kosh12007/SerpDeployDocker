import logging
from .db.database import create_connection

logger = logging.getLogger(__name__)

def get_region_name_by_id(search_engine, region_id):
    """Возвращает имя региона по его ID в зависимости от поисковой системы."""
    
    connection = create_connection()
    if not connection:
        return str(region_id)

    try:
        cursor = connection.cursor(dictionary=True)
        if search_engine == 'yandex':
            cursor.execute("SELECT region_name FROM yandex_regions WHERE region_id = %s", (region_id,))
            result = cursor.fetchone()
            return result['region_name'] if result else str(region_id)
        else: # google
            cursor.execute("SELECT canonical_name FROM locations WHERE criteria_id = %s", (region_id,))
            result = cursor.fetchone()
            return result['canonical_name'] if result else str(region_id)
    except Exception as e:
        logger.error(f"Ошибка при получении имени региона: {e}")
        return str(region_id)
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()