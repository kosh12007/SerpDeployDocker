# План создания файлов blueprints

## Цель
Создать файлы для каждого функционального блока в соответствии с планом рефакторинга routes.py.

## Структура директории
Создать директорию `../serp/app/blueprints/` и в ней следующие файлы:

### 1. `../serp/app/blueprints/__init__.py`
```python
"""
Blueprints package for SERP bot application.

Contains modularized route handlers separated by functionality:
- Main routes
- Parsing routes  
- Page analyzer routes
- AI routes
- API routes
"""

# This file makes blueprints a Python package
```

### 2. `../serp/app/blueprints/main_routes.py`
```python
"""
Main routes blueprint for SERP bot application.

Contains core application routes such as:
- Home page
- Results page
- Balance checking
- Import pages
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import os
import logging
from ..config import MODE
from ..db.database import (
    get_db_connection, get_user_sessions_from_db,
    get_results_from_db, execute_sql_from_file, get_yandex_regions
)
from ..parsing import parsing_status
from mysql.connector import Error
from ..import_locations import import_locations_from_csv

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'main_routes.log')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
logger.info(f"Логгер для {__name__} настроен.")
# --- Конец настройки логгера ---

main_routes = Blueprint('main', __name__)

@main_routes.context_processor
def inject_user():
    """
    Внедряет информацию о текущем пользователе во все шаблоны,
    связанные с этим blueprint. Это позволяет получить доступ к
    `current_user` в базовом шаблоне `layout.html` и других.
    """
    return dict(current_user=current_user)

@main_routes.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    try:
        sessions = get_user_sessions_from_db(current_user.id)
        return render_template("index.html", sessions=sessions, max_queries=int(os.getenv('MAX_QUERIES', 5)))
    except Exception as e:
        logger.error(f"Ошибка рендеринга шаблона index.html: {e}", exc_info=True)
        return f"Ошибка рендеринга шаблона: {str(e)}"

@main_routes.route("/show-results")
@login_required
def show_results():
    session_id = request.args.get('session_id')
    
    if session_id:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM parsing_sessions WHERE session_id = %s AND user_id = %s",
                (session_id, current_user.id)
            )
            session_data = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not session_data:
                flash("У вас нет доступа к этой сессии", "danger")
                return redirect(url_for('main.show-results'))
        else:
            flash("Ошибка подключения к базе данных", "danger")
            return redirect(url_for('main.show-results'))
        
        if parsing_status['error']:
            return f"<h2>Ошибка:</h2><p>{parsing_status['error']}</p><a href='/'>Вернуться на главную</a>"
        
        results = get_results_from_db(session_id)
        
        positions = [int(r['position']) for r in results if r['position'] and r['position'] != '-']
        if positions:
            avg_position = sum(positions) / len(positions)
            top_10 = len([p for p in positions if p <= 10])
        else:
            avg_position = 0
            top_10 = 0
        
        all_sessions = get_user_sessions_from_db(current_user.id)
        return render_template("results.html", results=results, avg_position=avg_position, top_10=top_10, session_id=session_id, sessions=all_sessions, session_info=session_data)
    
    else:
        sessions = get_user_sessions_from_db(current_user.id)
        return render_template("results.html", sessions=sessions)

@main_routes.route("/get-balance")
@login_required
def get_balance():
    try:
        api_url = os.getenv("API_KEY")
        if not api_url:
            raise ValueError("API_KEY не найден в .env")

        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(api_url)
        query_params = parse_qs(parsed_url.query)
        user = query_params.get("user", [None])[0]
        key = query_params.get("key", [None])[0]

        if not user or not key:
            raise ValueError("Не удалось извлечь user или key из API_KEY")

        balance_url = "https://xmlriver.com/api/get_balance/"
        params = {"user": user, "key": key}
        
        import requests
        response = requests.get(balance_url, params=params)
        response.raise_for_status()

        return jsonify({"balance": response.text.strip()})

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса к API баланса: {e}", exc_info=True)
        return jsonify({"error": f"Ошибка запроса к API: {e}"}), 500
    except ValueError as e:
        logger.error(f"Ошибка значения при получении баланса: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при получении баланса: {e}", exc_info=True)
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500

@main_routes.route('/import-locations')
@login_required
def import_locations_page():
    """Отображает страницу для запуска импорта локаций."""
    return render_template('import.html')

@main_routes.route('/run-import-locations', methods=['POST'])
@login_required
def run_import_locations():
    """Запускает импорт локаций из CSV файла."""
    try:
        import threading
        # Путь к файлу geo (1).csv относительно корня проекта
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'geo (1).csv')
        
        # Запускаем импорт в отдельном потоке, чтобы не блокировать основной процесс
        thread = threading.Thread(target=import_locations_from_csv, args=(filepath,))
        thread.start()
        
        flash('Процесс импорта запущен в фоновом режиме. Это может занять некоторое время.', 'info')
    except Exception as e:
        logger.error(f"Ошибка при запуске потока импорта: {e}", exc_info=True)
        flash(f'Произошла ошибка при запуске импорта: {e}', 'danger')
        
    return redirect(url_for('main.import_locations_page'))

@main_routes.route('/import-yandex-regions')
@login_required
def yandex_regions_import_page():
    """Отображает страницу для запуска импорта регионов Яндекса."""
    return render_template('yandex_regions_import.html')

@main_routes.route('/run-yandex-regions-import', methods=['POST'])
@login_required
def run_yandex_regions_import():
    """Запускает выполнение SQL-скрипта для создания и заполнения таблицы регионов Яндекса."""
    try:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'yandex_regions.sql')
        success, message = execute_sql_from_file(filepath)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    except Exception as e:
        logger.error(f"Ошибка при запуске импорта регионов Яндекса: {e}", exc_info=True)
        flash(f'Произошла ошибка при запуске импорта: {e}', 'danger')
        
    return redirect(url_for('main.yandex_regions_import_page'))
```

### 3. `../serp/app/blueprints/parsing_routes.py`
```python
"""
Parsing routes blueprint for SERP bot application.

Contains routes for:
- Running parsing tasks
- Checking parsing status
- Downloading parsing results
- Managing parsing sessions
- Top sites parsing
- Limits estimation
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, Response
from flask_login import login_required, current_user
import os
import logging
import threading
import datetime
import uuid
import io
import csv
import pandas as pd
from ..config import MODE
from ..db.database import (
    create_connection, get_db_connection, get_user_sessions_from_db,
    get_results_from_db, update_session_status, spend_limit
)
from ..parsing import run_parsing_in_thread, run_top_sites_parsing_thread, parsing_status
from ..utils import assign_duplicate_styles
from mysql.connector import Error
from ..region_utils import get_region_name_by_id

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'parsing_routes.log')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
logger.info(f"Логгер для {__name__} настроен.")
# --- Конец настройки логгера ---

parsing_routes = Blueprint('parsing', __name__)

@parsing_routes.route("/run", methods=["POST"])
@login_required
def run_parser():
    global parsing_status
    
    if parsing_status['is_running']:
        logger.warning("Попытка запустить парсинг, когда он уже выполняется.")
        return jsonify({"error": "Парсинг уже выполняется, дождитесь завершения предыдущего процесса"}), 400
    
    engine = request.form.get("engine", "google")
    queries = request.form.get("queries", "")
    domain = request.form.get("domain", "")
    yandex_type = request.form.get("yandex_type", "search_api")
    yandex_page_limit = request.form.get("yandex_page_limit", "9")
    google_page_limit = request.form.get("google_page_limit", "10")
    device = 'desktop' # Устанавливаем значение по умолчанию
    
    loc_id_google = request.form.get('loc_id_google')
    loc_id_yandex = request.form.get('loc_id_yandex')

    if engine == 'google':
        try:
            loc_id = int(loc_id_google) if loc_id_google and loc_id_google != 'undefined' else 20949
            depth = int(google_page_limit)
        except (ValueError, TypeError):
            depth = 10
    else:
        try:
            loc_id = int(loc_id_yandex) if loc_id_yandex and loc_id_yandex != 'undefined' else 213
            depth = int(yandex_page_limit)
        except (ValueError, TypeError):
            depth = 9

    print(f"Парсинг Топа: {engine}")
    print(f"Парсинг Топа: {yandex_type}")
    print(f"Парсинг Топа: {queries}")
    print(f"Локация: {loc_id}")
    
    mode = MODE

    session_id = f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            insert_query = """
            INSERT INTO parsing_sessions (session_id, domain, engine, user_id, region, device, depth, yandex_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (session_id, domain, engine, current_user.id, loc_id, device, depth, yandex_type if engine == 'yandex' else None))
            connection.commit()
            cursor.close()
            connection.close()
        else:
            return "Ошибка при создании сессии парсинга"
    except Error as e:
        logger.error(f"Ошибка создания сессии в базе данных: {e}", exc_info=True)
        return "Ошибка при создании сессии парсинга"
    
    logger.info(f"Запуск потока парсинга для сессии {session_id}")
    thread = threading.Thread(
        target=run_parsing_in_thread,
        args=(engine, queries, domain, mode, session_id, current_user.id, yandex_type, yandex_page_limit, google_page_limit)
    )
    thread.start()
    
    return jsonify({"status": "started", "message": "Парсинг запущен", "session_id": session_id})

@parsing_routes.route("/status")
@login_required
def get_status():
    global parsing_status
    
    # Получаем текущую сессию, если она есть
    session_id = parsing_status.get('session_id')
    spent_limits = 0
    
    if session_id:
        try:
            connection = create_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute(
                    "SELECT spent_limits FROM parsing_sessions WHERE session_id = %s",
                    (session_id,)
                )
                result = cursor.fetchone()
                if result and result['spent_limits'] is not None:
                    spent_limits = result['spent_limits']
                cursor.close()
                connection.close()
        except Error as e:
            logger.error(f"Ошибка получения spent_limits для сессии {session_id}: {e}")

    # Копируем статус и добавляем/обновляем spent_limits
    status_response = parsing_status.copy()
    status_response['spent_limits'] = spent_limits
    
    return jsonify(status_response)

@parsing_routes.route("/download-session-results/<session_id>")
@login_required
def download_session_results(session_id):
    from flask import Response
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM parsing_sessions WHERE session_id = %s AND user_id = %s",
            (session_id, current_user.id)
        )
        session_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not session_data:
            flash("У вас нет доступа к этой сессии", "danger")
            return redirect(url_for('main.show-results'))
    else:
        flash("Ошибка подключения к базе данных", "danger")
        return redirect(url_for('main.show-results'))
    
    format_type = request.args.get('format', 'xlsx')
    
    results = get_results_from_db(session_id)
    
    if not results:
        return "Нет данных для скачивания", 404
    
    if format_type == 'txt':
        output = io.StringIO()
        for result in results:
            output.write(f"Запрос: {result.get('query', result.get('Query', ''))}\n")
            output.write(f"Позиция: {result.get('position', result.get('Position', ''))}\n")
            output.write(f"URL: {result.get('url', result.get('URL', ''))}\n")
            output.write(f"Статус: {result.get('processed', result.get('Processed', ''))}\n")
            output.write("---\n")
        
        txt_content = output.getvalue()
        output.close()
        
        return Response(
            txt_content,
            mimetype="text/plain",
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}.txt"}
        )
    
    elif format_type == 'csv_utf8' or format_type == 'csv_win1251':
        encoding = 'utf-8' if format_type == 'csv_utf8' else 'windows-1251'
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Запрос', 'Позиция', 'URL', 'Статус'])
        
        for result in results:
            row = [
                result.get('query', result.get('Query', '')),
                result.get('position', result.get('Position', '')),
                result.get('url', result.get('URL', '')),
                result.get('processed', result.get('Processed', ''))
            ]
            writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        return Response(
            csv_content.encode(encoding),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}_{encoding}.csv"}
        )
    
    else:  # xlsx по умолчанию
        data = []
        for result in results:
            data.append({
                'Запрос': result.get('query', result.get('Query', '')),
                'Позиция': result.get('position', result.get('Position', '')),
                'URL': result.get('url', result.get('URL', '')),
                'Статус': result.get('processed', result.get('Processed', ''))
            })
        
        df = pd.DataFrame(data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Results')
        
        output.seek(0)
        
        from flask import send_file
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"session_{session_id}.xlsx"
        )

@parsing_routes.route("/delete-session/<session_id>", methods=["DELETE"])
@login_required
def delete_session(session_id):
    try:
        connection = create_connection()
        if not connection:
            return jsonify({'status': 'error', 'message': 'Ошибка подключения к базе данных'}), 500

        cursor = connection.cursor()

        cursor.execute(
            "SELECT user_id FROM parsing_sessions WHERE session_id = %s",
            (session_id,)
        )
        session_owner = cursor.fetchone()

        if not session_owner:
            cursor.close()
            connection.close()
            return jsonify({'status': 'error', 'message': 'Сессия не найдена'}), 404

        if session_owner[0] != current_user.id:
            cursor.close()
            connection.close()
            return jsonify({'status': 'error', 'message': 'У вас нет прав на удаление этой сессии'}), 403

        delete_query = "DELETE FROM parsing_sessions WHERE session_id = %s AND user_id = %s"
        cursor.execute(delete_query, (session_id, current_user.id))
        
        if cursor.rowcount == 0:
            cursor.close()
            connection.close()
            return jsonify({'status': 'error', 'message': 'Сессия не найдена или уже удалена'}), 404

        connection.commit()
        
        cursor.close()
        connection.close()

        return jsonify({'status': 'success', 'message': 'Сессия и все связанные данные успешно удалены'})

    except Error as e:
        logger.error(f"Ошибка базы данных при удалении сессии {session_id}: {e}", exc_info=True)
        if 'connection' in locals() and connection.is_connected():
            connection.rollback()
        return jsonify({'status': 'error', 'message': 'Ошибка базы данных при удалении сессии'}), 500
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при удалении сессии {session_id}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Внутренняя ошибка сервера'}), 500
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()

@parsing_routes.route('/start-top-sites-parsing', methods=['POST'])
@login_required
def start_top_sites_parsing():
    try:
        # queries_text = request.form.get('queries')
        queries_list = request.form.getlist('queries')
        search_engine = request.form.get('search_engine')
        # region = request.form.get('region') # Это поле больше не используется напрямую
        device = request.form.get('device')
        depth_str = request.form.get('depth')
        depth = int(depth_str) if depth_str and depth_str.isdigit() else 1
        yandex_type = request.form.get('yandex_type', 'search_api')
        
        yandex_page_limit_str = request.form.get('yandex_page_limit')
        yandex_page_limit = int(yandex_page_limit_str) if yandex_page_limit_str and yandex_page_limit_str.isdigit() else 1
        
        google_page_limit_str = request.form.get('google_page_limit')
        google_page_limit = int(google_page_limit_str) if google_page_limit_str and google_page_limit_str.isdigit() else 1
        # Determine which loc_id to use
        # loc_id теперь передается как единое поле, не зависимо от поисковика
        loc_id_str = request.form.get('loc_id')
        if loc_id_str and loc_id_str != 'undefined':
            loc_id = int(loc_id_str)
        else:
            # Если loc_id не предоставлен или 'undefined', используем значение по умолчанию
            loc_id = 213 if request.form.get('search_engine') == 'yandex' else 20949
            
        user_id = current_user.id
        # Объединяем список фраз обратно в текст, разделенный новой строкой, если это необходимо для дальнейшей обработки
        queries_text = '\n'.join(queries_list)
        logger.info(f"Запуск парсинга ТОП-10. Движок: {search_engine}, Тип Яндекса: {yandex_type}, Глубина: {depth}, Лимит страниц Yandex: {yandex_page_limit}, Лимит страниц Google: {google_page_limit}, Локация: {loc_id}")
        logger.debug(f"Параметры парсинга ТОП-10: queries_list={queries_list}, search_engine={search_engine}, device={device}, depth={depth}, yandex_type={yandex_type}, yandex_page_limit={yandex_page_limit}, google_page_limit={google_page_limit}, loc_id={loc_id}")

        queries = [q.strip() for q in queries_list if q.strip()]
        if not all([queries, search_engine, loc_id, device]):
            return jsonify({"error": "Отсутствуют обязательные параметры."}), 400

        # --- Проверка лимитов (основная логика вынесена в /estimate-limits) ---
        # Оставляем проверку на сервере для безопасности
        required_limits = 0
        queries_count = len(queries)
        if search_engine == 'yandex' and yandex_type == 'search_api':
            required_limits = queries_count
        else:
            page_limit = google_page_limit if search_engine == 'google' else yandex_page_limit
            required_limits = queries_count * page_limit

        if current_user.limits < required_limits:
            return jsonify({
                "error": f"Недостаточно лимитов для выполнения задачи. Требуется: {required_limits}, у вас в наличии: {current_user.limits}."
            }), 400
        # --- Конец проверки ---

        connection = create_connection()
        if not connection:
            return jsonify({"error": "Не удалось подключиться к базе данных."}), 500
        
        cursor = connection.cursor()

        task_sql = """
        INSERT INTO top_sites_tasks (user_id, search_engine, region, device, depth, status, yandex_type)
        VALUES (%s, %s, %s, %s, %s, 'running', %s)
        """
        cursor.execute(task_sql, (user_id, search_engine, loc_id, device, depth, yandex_type if search_engine == 'yandex' else None))
        task_id = cursor.lastrowid

        queries_to_process = []
        for query_text in queries:
            query_sql = "INSERT INTO top_sites_queries (task_id, query_text) VALUES (%s, %s) "
            cursor.execute(query_sql, (task_id, query_text))
            query_id = cursor.lastrowid
            queries_to_process.append({'id': query_id, 'text': query_text})
        
        connection.commit()

        thread = threading.Thread(
            target=run_top_sites_parsing_thread,
            args=(task_id, queries_to_process, search_engine, loc_id, device, depth, yandex_type, yandex_page_limit, google_page_limit, user_id)
        )
        thread.start()

        return jsonify({
            "status": "success",
            "message": f"Задача парсинга ТОП-10 запущена для {len(queries)} фраз. Будет списано примерно {required_limits} лимитов.",
            "task_id": task_id
        })

    except Exception as e:
        logger.error(f"Ошибка при запуске задачи парсинга ТОП-10: {e}", exc_info=True)
        if 'connection' in locals() and connection.is_connected():
            connection.rollback()
        return jsonify({"error": "Внутренняя ошибка сервера при запуске задачи."}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()

@parsing_routes.route('/estimate-limits', methods=['POST'])
@login_required
def estimate_limits():
   """
   Оценивает и возвращает необходимое количество лимитов для задачи парсинга.
   """
   try:
       logger.debug(f"Запрос на оценку лимитов. Request form: {request.form}")
       # Данные приходят как form-data, а не JSON. Используем request.form.
       # request.form.getlist используется для получения всех значений с одинаковым именем,
       # на случай если фронтенд будет отправлять несколько полей 'queries'.
       queries_list = request.form.getlist('queries')
       search_engine = request.form.get('search_engine')
       yandex_type = request.form.get('yandex_type', 'search_api')
       yandex_page_limit = int(request.form.get('yandex_page_limit', 1))
       google_page_limit = int(request.form.get('google_page_limit', 1))

       queries = [q.strip() for q in queries_list if q.strip()]
       if not queries:
           return jsonify({"error": "Список запросов пуст."}), 400

       # --- Логика прогнозирования лимитов ---
       required_limits = 0
       queries_count = len(queries)

       if search_engine == 'yandex' and yandex_type == 'search_api':
           required_limits = queries_count
       else:  # Live Search или Google
           page_limit = google_page_limit if search_engine == 'google' else yandex_page_limit
           required_limits = queries_count * page_limit

       return jsonify({
           "estimated_limits": required_limits,
           "available_limits": current_user.limits
       })

   except Exception as e:
       logger.error(f"Ошибка при оценке лимитов: {e}", exc_info=True)
       return jsonify({"error": "Внутренняя ошибка сервера при оценке лимитов."}), 500


@parsing_routes.route('/estimate-limits-parser', methods=['POST'])
@login_required
def estimate_limits_parser():
  """
  Оценивает и возвращает необходимое количество лимитов для задачи парсинга позиций.
  """
  try:
      logger.debug(f"Запрос на оценку лимитов парсера. Request form: {request.form}")
      queries_text = request.form.get('queries', '')
      engine = request.form.get('engine')
      yandex_type = request.form.get('yandex_type', 'search_api')
      yandex_page_limit = int(request.form.get('yandex_page_limit', 1))
      google_page_limit = int(request.form.get('google_page_limit', 1))

      queries = [q.strip() for q in queries_text.splitlines() if q.strip()]
      if not queries:
          return jsonify({"error": "Список запросов пуст."}), 400

      required_limits = 0
      queries_count = len(queries)

      if engine == 'yandex' and yandex_type == 'search_api':
          required_limits = queries_count
      else:  # Live Search или Google
          page_limit = google_page_limit if engine == 'google' else yandex_page_limit
          required_limits = queries_count * page_limit

      return jsonify({
          "estimated_limits": required_limits,
          "available_limits": current_user.limits
      })

  except Exception as e:
      logger.error(f"Ошибка при оценке лимитов парсера: {e}", exc_info=True)
      return jsonify({"error": "Внутренняя ошибка сервера при оценке лимитов."}), 500

@parsing_routes.route("/download-top-sites/<int:task_id>")
@login_required
def download_top_sites_task(task_id):
    from flask import send_file

    format_type = request.args.get('format', 'xlsx')

    connection = create_connection()
    if not connection:
        flash("Ошибка подключения к базе данных.", "danger")
        return redirect(url_for('top_sites.top_sites_page'))

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT * FROM top_sites_tasks WHERE id = %s AND user_id = %s", (task_id, current_user.id))
        task_info = cursor.fetchone()

        if not task_info:
            flash("Задача не найдена или у вас нет к ней доступа.", "danger")
            return redirect(url_for('top_sites.top_sites_page'))

        # Получаем первую фразу для имени файла
        cursor.execute("SELECT query_text FROM top_sites_queries WHERE task_id = %s ORDER BY id LIMIT 1", (task_id,))
        first_query = cursor.fetchone()
        first_query_text = first_query['query_text'].replace(" ", "_") if first_query else ""
        
        # Получаем имя региона
        region_name = get_region_name_by_id(task_info.get('search_engine'), task_info.get('region'))


        # Формируем имя файла
        filename_parts = [
            f"Задача_{task_id}",
            task_info['search_engine'],
        ]
        if task_info.get('yandex_type'):
            filename_parts.append(task_info['yandex_type'])
        
        filename_parts.extend([
            region_name,
            task_info['device'],
            task_info['created_at'].strftime('%Y-%m-%d'),
            first_query_text
        ])
        
        base_filename = "_".join(filter(None, filename_parts))

        sql = """
        SELECT tq.query_text, tr.position, tr.url
        FROM top_sites_results tr
        JOIN top_sites_queries tq ON tr.query_id = tq.id
        WHERE tq.task_id = %s
        ORDER BY tq.id, tr.position
        """
        cursor.execute(sql, (task_id,))
        results = cursor.fetchall()

        if not results:
            flash("Нет данных для скачивания по этой задаче.", "warning")
            return redirect(url_for('top_sites.top_sites_page'))

        if format_type == 'csv_utf8' or format_type == 'csv_win1251':
            encoding = 'utf-8' if format_type == 'csv_utf8' else 'windows-1251'
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Запрос', 'Позиция', 'URL'])
            for res in results:
                writer.writerow([res['query_text'], res['position'], res['url']])

            output.seek(0)
            return send_file(
                io.BytesIO(output.read().encode(encoding)),
                mimetype="text/csv",
                as_attachment=True,
                download_name=f"{base_filename}.csv"
            )
        elif format_type == 'txt':
            output = io.StringIO()
            current_query = None
            for res in results:
                if res['query_text'] != current_query:
                    current_query = res['query_text']
                    output.write(f"\n--- Результаты для запроса: {current_query} ---\n")
                output.write(f"{res['position']}. {res['url']}\n")
            
            output.seek(0)
            return send_file(
                io.BytesIO(output.read().encode('utf-8')),
                mimetype="text/plain",
                as_attachment=True,
                download_name=f"{base_filename}.txt"
            )
        else: # xlsx по умолчанию
            df = pd.DataFrame(results, columns=['query_text', 'position', 'url'])
            df.rename(columns={'query_text': 'Запрос', 'position': 'Позиция', 'url': 'URL'}, inplace=True)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name=f'Task_{task_id}')
            output.seek(0)
            
            return send_file(
                output,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=f"{base_filename}.xlsx"
            )

    except Error as e:
        logger.error(f"Ошибка базы данных при скачивании результатов задачи {task_id}: {e}", exc_info=True)
        flash("Ошибка базы данных при формировании файла.", "danger")
        return redirect(url_for('top_sites.top_sites_page'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@parsing_routes.route("/delete-top-sites/<int:task_id>", methods=["DELETE"])
@login_required
def delete_top_sites_task(task_id):
    connection = create_connection()
    if not connection:
        return jsonify({"status": "error", "message": "Ошибка подключения к базе данных."}), 500

    try:
        cursor = connection.cursor()
        
        cursor.execute("SELECT user_id FROM top_sites_tasks WHERE id = %s", (task_id,))
        task = cursor.fetchone()
        if not task or task[0] != current_user.id:
            return jsonify({"status": "error", "message": "У вас нет прав на удаление этой задачи."}), 403

        cursor.execute("DELETE FROM top_sites_tasks WHERE id = %s", (task_id,))
        connection.commit()
        
        return jsonify({"status": "success", "message": "Задача и все связанные данные успешно удалены."})

    except Error as e:
        logger.error(f"Ошибка базы данных при удалении задачи {task_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Ошибка базы данных при удалении."}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@top_sites_routes.route("/top-sites")
@login_required
def top_sites_page():
    """Отображает страницу 'Выгрузка ТОП-10 сайтов' с формой и результатами."""
    connection = create_connection()
    if not connection:
        flash("Ошибка подключения к базе данных.", "danger")
        return render_template('top_sites.html', tasks_data=[], max_queries=int(os.getenv('MAX_QUERIES', 5)))

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM top_sites_tasks WHERE user_id = %s ORDER BY created_at DESC",
            (current_user.id,)
        )
        tasks = cursor.fetchall()

        tasks_data = []
        for task in tasks:
            task['region_name'] = get_region_name_by_id(task.get('search_engine'), task.get('region'))
            cursor.execute("SELECT * FROM top_sites_queries WHERE task_id = %s", (task['id'],))
            task_queries = cursor.fetchall()
            logger.debug(f"Task {task['id']} queries: {task_queries}")
            
            all_results_for_task = []
            query_ids_for_task = [q['id'] for q in task_queries]

            if query_ids_for_task:
                placeholders = ','.join(['%s'] * len(query_ids_for_task))
                result_sql = f"SELECT * FROM top_sites_results WHERE query_id IN ({placeholders}) ORDER BY position ASC"
                cursor.execute(result_sql, tuple(query_ids_for_task))
                all_results_for_task = cursor.fetchall()

            results_by_query_id = {}
            for res in all_results_for_task:
                q_id = res['query_id']
                if q_id not in results_by_query_id:
                    results_by_query_id[q_id] = []
                results_by_query_id[q_id].append(res)
            
            for q in task_queries:
                q['results'] = results_by_query_id.get(q['id'], [])

            # Собираем все URL-ы из всех запросов в один список
            all_urls_for_task = [r['url'] for q in task_queries for r in q['results']]
            logger.debug(f"All URLs for task {task['id']} sent to assign_duplicate_styles: {all_urls_for_task}")

            duplicate_styles = assign_duplicate_styles(all_urls_for_task)
            logger.debug(f"Result from assign_duplicate_styles for task {task['id']}: {duplicate_styles}")

            tasks_data.append({
                'task_info': task,
                'queries': task_queries,
                'duplicate_styles': duplicate_styles
            })
        
        max_queries = int(os.getenv('MAX_QUERIES', 5))
        return render_template('top_sites.html', tasks_data=tasks_data, max_queries=max_queries)

    except Error as e:
        logger.error(f"Ошибка при получении данных для страницы 'ТОП-10': {e}", exc_info=True)
        flash("Произошла ошибка при получении данных.", "danger")
        return render_template('top_sites.html', tasks_data=[], max_queries=int(os.getenv('MAX_QUERIES', 5)))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
```

### 4. `../serp/app/blueprints/page_analyzer_routes.py`
```python
"""
Page analyzer routes blueprint for SERP bot application.

Contains routes for:
- Page analyzer page
- Analyzing pages
- Checking analysis status
- Downloading analysis results
- Deleting analysis tasks
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, Response
from flask_login import login_required, current_user
import os
import logging
import io
import csv
import pandas as pd
import json
from ..db.database import create_connection
from ..db.page_analyzer_db import create_page_analysis_task, save_page_analysis_result, delete_page_analysis_task
from ..page_analyzer_thread import start_analysis, analysis_status
from mysql.connector import Error

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'page_analyzer_routes.log')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
logger.info(f"Логгер для {__name__} настроен.")
# --- Конец настройки логгера ---

page_analyzer_routes = Blueprint('page_analyzer', __name__)

@page_analyzer_routes.route("/page-analyzer")
@login_required
def page_analyzer():
    """Отображает страницу анализатора страниц."""
    connection = create_connection()
    if not connection:
        flash("Ошибка подключения к базе данных.", "danger")
        return render_template('page_analyzer.html', tasks=[])
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM page_analysis_tasks WHERE user_id = %s ORDER BY created_at DESC", (current_user.id,))
        tasks = cursor.fetchall()
        
        for task in tasks:
            cursor.execute("SELECT * FROM page_analysis_results WHERE task_id = %s", (task['id'],))
            task['results'] = cursor.fetchall()
            
        return render_template("page_analyzer.html", tasks=tasks, from_json=json.loads)
    except Error as e:
        flash(f"Ошибка при загрузке задач: {e}", "danger")
        return render_template("page_analyzer.html", tasks=[])
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@page_analyzer_routes.route("/analyze-pages", methods=["POST"])
@login_required
def analyze_pages():
    """Обрабатывает запрос на анализ нескольких страниц."""
    data = request.get_json()
    urls_input = data.get('urls')

    if not urls_input:
        return jsonify({"error": "URL не указаны"}), 400

    # Разделяем строку по http:// и https://, сохраняя разделители
    import re
    urls_raw = re.split(r'(https?://)', ''.join(urls_input))
    
    urls = []
    for i in range(1, len(urls_raw), 2):
        # Соединяем протокол (http:// или https://) со следующей частью URL
        # и очищаем от лишних пробелов
        full_url = (urls_raw[i] + urls_raw[i+1]).strip()
        if full_url:
            urls.append(full_url)
    
    if not urls:
        return jsonify({"error": "Корректные URL не найдены"}), 400

    task_id = create_page_analysis_task(current_user.id)
    if not task_id:
        return jsonify({"error": "Не удалось создать задачу для анализа"}), 500

    start_analysis(task_id, urls)

    return jsonify({"status": "started", "task_id": task_id})

@page_analyzer_routes.route("/analysis-status/<int:task_id>")
@login_required
def analysis_status_route(task_id):
    """Возвращает статус задачи анализа."""
    status = analysis_status.get(task_id, {
        'total': 0,
        'completed': 0,
        'status': 'not_found',
        'progress': 0
    })
    return jsonify(status)

@page_analyzer_routes.route("/download-analysis/<int:task_id>")
@login_required
def download_analysis_task(task_id):
    from flask import send_file

    format_type = request.args.get('format', 'xlsx')

    connection = create_connection()
    if not connection:
        flash("Ошибка подключения к базе данных.", "danger")
        return redirect(url_for('main.page_analyzer'))

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT * FROM page_analysis_tasks WHERE id = %s AND user_id = %s", (task_id, current_user.id))
        task_info = cursor.fetchone()

        if not task_info:
            flash("Задача не найдена или у вас нет к ней доступа.", "danger")
            return redirect(url_for('main.page_analyzer'))
            
        cursor.execute("SELECT * FROM page_analysis_results WHERE task_id = %s", (task_id,))
        results = cursor.fetchall()

        if not results:
            flash("Нет данных для скачивания по этой задаче.", "warning")
            return redirect(url_for('main.page_analyzer'))

        base_filename = f"Analysis_Task_{task_id}_{task_info['created_at'].strftime('%Y-%m-%d')}"

        # --- Подготовка данных в формате XLSX ---
        import html
        new_results = []
        for res in results:
            lsi_words = []
            if res['lsi_words'] and isinstance(res['lsi_words'], str):
                try:
                    lsi_data = json.loads(res['lsi_words'])
                    # Если lsi_data - это строка (из-за двойного кодирования), пробуем декодировать еще раз
                    if isinstance(lsi_data, str):
                        lsi_data = json.loads(lsi_data)
                    if isinstance(lsi_data, list):
                        lsi_words = lsi_data                       
                except (json.JSONDecodeError, TypeError):
                    # Если это просто строка, не являющаяся JSON, оставляем как есть
                    lsi_words = [res['lsi_words']]

            headings = json.loads(res['headings']) if res['headings'] and isinstance(res['headings'], str) else []
            
            max_len = max(len(lsi_words), len(headings), 1)
            
            for i in range(max_len):
                new_row = {
                    'url': res['url'] if i == 0 else '',
                    'title': html.unescape(res['title']) if i == 0 and res['title'] else '',
                    'description': html.unescape(res['description']) if i == 0 and res['description'] else '',
                    'text_length': res['text_length'] if i == 0 else '',
                    'lsi_word': lsi_words[i] if i < len(lsi_words) else '',
                    'heading_level': f"H{headings[i]['level']}" if i < len(headings) else '',
                    'heading_text': html.unescape(headings[i]['text']) if i < len(headings) and headings[i].get('text') else '',
                }
                new_results.append(new_row)

        df = pd.DataFrame(new_results)
        
        # --- Перевод заголовков ---
        df.rename(columns={
            'url': 'URL',
            'title': 'Title',
            'description': 'Description',
            'text_length': 'Длина текста',
            'lsi_word': 'LSI-слова',
            'heading_level': 'Уровень заголовка',
            'heading_text': 'Текст заголовка'
        }, inplace=True)

        # --- Выгрузка в запрошенном формате ---
        if format_type == 'csv_utf8' or format_type == 'csv_win1251':
            encoding = 'utf-8' if format_type == 'csv_utf8' else 'windows-1251'
            output = io.StringIO()
            df.to_csv(output, index=False, quoting=csv.QUOTE_NONNUMERIC)
            csv_data = output.getvalue()
            output.close()
            
            response_data = io.BytesIO(csv_data.encode(encoding, errors='replace'))
            
            return send_file(
                response_data,
                mimetype="text/csv",
                as_attachment=True,
                download_name=f"{base_filename}.csv"
            )
        elif format_type == 'txt':
            output = io.StringIO()
            # Используем исходные 'results' для более компактного вывода
            for res in results:
                output.write(f"--- URL: {res['url']} ---\n")
                output.write(f"Title: {html.unescape(res['title']) if res['title'] else ''}\n")
                output.write(f"Description: {html.unescape(res['description']) if res['description'] else ''}\n")
                output.write(f"Длина текста: {res['text_length']}\n")
                
                lsi_words_str = 'N/A'
                if res['lsi_words'] and isinstance(res['lsi_words'], str):
                    try:
                        lsi_data = json.loads(res['lsi_words'])
                        if isinstance(lsi_data, list):
                            lsi_words_str = ', '.join(lsi_data)
                        else:
                            lsi_words_str = str(lsi_data)
                    except (json.JSONDecodeError, TypeError):
                        lsi_words_str = res['lsi_words'] # Если это уже строка, а не JSON
                output.write(f"LSI-слова: {lsi_words_str}\n")
                
                headings_str = 'N/A'
                if res['headings'] and isinstance(res['headings'], str):
                    try:
                        headings_data = json.loads(res['headings'])
                        headings_str = '\n'.join([f"H{h['level']}: {html.unescape(h['text'])}" for h in headings_data])
                    except json.JSONDecodeError:
                        pass
                output.write(f"Заголовки:\n{headings_str}\n\n")

            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype="text/plain",
                as_attachment=True,
                download_name=f"{base_filename}.txt"
            )
        else: # xlsx по умолчанию
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name=f'Task_{task_id}')
            output.seek(0)
            
            return send_file(
                output,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=f"{base_filename}.xlsx"
            )

    except Error as e:
        logger.error(f"Ошибка базы данных при скачивании результатов задачи {task_id}: {e}", exc_info=True)
        flash("Ошибка базы данных при формировании файла.", "danger")
        return redirect(url_for('main.page_analyzer'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@page_analyzer_routes.route("/delete-analysis/<int:task_id>", methods=["DELETE"])
@login_required
def delete_analysis_task_route(task_id):
    if delete_page_analysis_task(task_id, current_user.id):
        return jsonify({"status": "success", "message": "Задача успешно удалена."})
    else:
        return jsonify({"status": "error", "message": "Ошибка при удалении задачи."}), 500
```

### 5. `../serp/app/blueprints/ai_routes.py`
```python
"""
AI routes blueprint for SERP bot application.

Contains routes for:
- AI assistant page
- Article generator page
- Sending requests to AI
- Checking AI task status
- Downloading AI results
- Deleting AI tasks
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, Response
from flask_login import login_required, current_user
import os
import logging
import io
from ..config import DEEPSEEK_API_KEY
from ..db.database import create_connection
from ..db.ai_db import create_ai_task, get_ai_tasks_by_user, get_ai_results_by_task, delete_ai_task as db_delete_ai_task
from ..ai_thread import start_ai_analysis, ai_analysis_status
from mysql.connector import Error

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'ai_routes.log')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
logger.info(f"Логгер для {__name__} настроен.")
# --- Конец настройки логгера ---

ai_routes = Blueprint('ai', __name__)

@ai_routes.route("/ai")
@login_required
def ai_page():
    """Отображает страницу AI ассистента с задачами и результатами."""
    tasks = get_ai_tasks_by_user(current_user.id)
    for task in tasks:
        task['results'] = get_ai_results_by_task(task['id'])
    return render_template("ai.html", tasks=tasks)

@ai_routes.route("/article-generator")
@login_required
def article_generator_page():
    """Отображает страницу генератора статей с задачами и результатами."""
    tasks = get_ai_tasks_by_user(current_user.id)
    for task in tasks:
        task['results'] = get_ai_results_by_task(task['id'])
    return render_template("article_generator.html", tasks=tasks)

@ai_routes.route("/ask-ai", methods=["POST"])
@login_required
def ask_ai():
    """Создает задачу для AI и запускает ее выполнение."""
    system_prompt = request.form.get('system_prompt')
    user_message = request.form.get('user_message')

    if not all([system_prompt, user_message]):
        flash("Системный промпт и сообщение пользователя не могут быть пустыми.", "danger")
        return redirect(url_for('ai.ai_page'))

    if not DEEPSEEK_API_KEY:
        flash("API-ключ для DeepSeek не настроен на сервере.", "danger")
        return redirect(url_for('ai.ai_page'))

    task_id = create_ai_task(current_user.id, system_prompt)
    
    if task_id:
        start_ai_analysis(task_id, system_prompt, user_message)
        # Возвращаем JSON вместо редиректа для AJAX-запроса
        return jsonify({"status": "success", "message": "AI-задача успешно создана и поставлена в очередь на выполнение."})
    else:
        # Возвращаем JSON с ошибкой
        return jsonify({"status": "error", "message": "Ошибка при создании AI-задачи в базе данных."}), 500

@ai_routes.route("/ai-status/<int:task_id>")
@login_required
def ai_status_route(task_id):
    """Возвращает статус выполнения AI-задачи."""
    status = ai_analysis_status.get(task_id, {
        'status': 'not_found',
        'progress': 0,
        'message': 'Задача не найдена'
    })
    return jsonify(status)

@ai_routes.route("/delete-ai-task/<int:task_id>", methods=["DELETE"])
@login_required
def delete_ai_task(task_id):
    """Удаляет AI-задачу и связанные с ней результаты."""
    if db_delete_ai_task(task_id, current_user.id):
        return jsonify({"status": "success", "message": "Задача и все связанные данные успешно удалены."})
    else:
        return jsonify({"status": "error", "message": "Ошибка при удалении задачи или у вас нет прав."}), 500

@ai_routes.route("/download-ai-task/<int:task_id>")
@login_required
def download_ai_task(task_id):
    """Скачивает результаты AI-задачи."""
    format_type = request.args.get('format', 'txt')

    connection = create_connection()
    if not connection:
        flash("Ошибка подключения к базе данных.", "danger")
        return redirect(url_for('ai.ai_page'))

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM ai_tasks WHERE id = %s AND user_id = %s", (task_id, current_user.id))
        task = cursor.fetchone()

        if not task:
            flash("Задача не найдена или у вас нет к ней доступа.", "danger")
            return redirect(url_for('ai.ai_page'))

        cursor.execute("SELECT * FROM ai_results WHERE task_id = %s", (task_id,))
        results = cursor.fetchall()

        if not results:
            flash("Нет данных для скачивания по этой задаче.", "warning")
            return redirect(url_for('ai.ai_page'))
            
        base_filename = f"AI_Task_{task_id}_{task['created_at'].strftime('%Y-%m-%d')}"
        
        output = io.StringIO()
        output.write(f"--- Задача #{task_id} ---\n")
        output.write(f"Дата создания: {task['created_at'].strftime('%Y-%m-%d %H:%M')}\n")
        output.write(f"Системный промпт: {task['system_prompt']}\n\n")
        
        for i, res in enumerate(results, 1):
            output.write(f"--- Запрос #{i} ---\n")
            output.write(f"Пользователь: {res['user_message']}\n")
            output.write(f"AI Ответ: {res['ai_response']}\n\n")

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/plain",
            headers={"Content-Disposition": f"attachment; filename={base_filename}.txt"}
        )

    except Error as e:
        logger.error(f"Ошибка базы данных при скачивании AI-задачи {task_id}: {e}", exc_info=True)
        flash("Ошибка базы данных при формировании файла.", "danger")
        return redirect(url_for('ai.ai_page'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@ai_routes.route("/download-article-task/<int:task_id>")
@login_required
def download_article_task(task_id):
    """Скачивает результаты AI-задачи для генератора статей."""
    format_type = request.args.get('format', 'txt')

    connection = create_connection()
    if not connection:
        flash("Ошибка подключения к базе данных.", "danger")
        return redirect(url_for('ai.article_generator_page'))

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM ai_tasks WHERE id = %s AND user_id = %s", (task_id, current_user.id))
        task = cursor.fetchone()

        if not task:
            flash("Задача не найдена или у вас нет к ней доступа.", "danger")
            return redirect(url_for('ai.article_generator_page'))

        cursor.execute("SELECT * FROM ai_results WHERE task_id = %s", (task_id,))
        results = cursor.fetchall()

        if not results:
            flash("Нет данных для скачивания по этой задаче.", "warning")
            return redirect(url_for('ai.article_generator_page'))
            
        base_filename = f"Article_Task_{task_id}_{task['created_at'].strftime('%Y-%m-%d')}"
        
        output = io.StringIO()
        output.write(f"--- Задача #{task_id} ---\n")
        output.write(f"Дата создания: {task['created_at'].strftime('%Y-%m-%d %H:%M')}\n")
        output.write(f"Системный промпт: {task['system_prompt']}\n\n")
        
        for i, res in enumerate(results, 1):
            output.write(f"--- Запрос #{i} ---\n")
            output.write(f"Параметры:\n{res['user_message']}\n")
            output.write(f"AI Ответ:\n{res['ai_response']}\n\n")

        output.seek(0)
        return Response(
            output.getvalue().encode('utf-8'),
            mimetype="text/plain",
            headers={"Content-Disposition": f"attachment; filename={base_filename}.txt"}
        )

    except Error as e:
        logger.error(f"Ошибка базы данных при скачивании AI-задачи {task_id}: {e}", exc_info=True)
        flash("Ошибка базы данных при формировании файла.", "danger")
        return redirect(url_for('ai.article_generator_page'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
```

### 6. `../serp/app/blueprints/api_routes.py`
```python
"""
API routes blueprint for SERP bot application.

Contains API routes for:
- Locations API
- Yandex regions API
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
import os
import logging
from ..db.database import get_locations, get_yandex_regions

# --- Настройка логгера ---
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'api_routes.log')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
logger.info(f"Логгер для {__name__} настроен.")
# --- Конец настройки логгера ---

api_routes = Blueprint('api', __name__)

@api_routes.route('/api/locations')
@login_required
def api_locations():
    """Возвращает список локаций с пагинацией и поиском."""
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
    result = get_locations(search_query=search_query, page=page)
    
    # Форматируем для Select2
    formatted_results = {
        "results": [{"id": loc["criteria_id"], "text": loc["canonical_name"]} for loc in result["locations"]],
        "pagination": {
            "more": (page * 30) < result["total_count"]
        }
    }
    return jsonify(formatted_results)

@api_routes.route('/api/yandex-regions')
@login_required
def api_yandex_regions():
    """Возвращает список регионов Яндекса с пагинацией и поиском."""
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
    result = get_yandex_regions(search_query=search_query, page=page)
    
    formatted_results = {
        "results": [{"id": region["region_id"], "text": region["region_name"]} for region in result["regions"]],
        "pagination": {
            "more": (page * 30) < result["total_count"]
        }
    }
    return jsonify(formatted_results)
```

## Обновление основного приложения

Также потребуется обновить файл `../serp/app/__init__.py` для импорта и регистрации новых blueprints:

```python
from flask import Flask
from flask_login import LoginManager
import os
import secrets
from datetime import datetime, timezone

# Инициализация приложения
application = Flask(__name__, static_folder='../static', template_folder='../templates')
application.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(application)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице'

# Регистрация кастомного фильтра для форматирования даты
@application.template_filter('date')
def format_datetime(value, format='%Y-%m-%d %H:%M'):
    """Форматирует объект datetime в строку."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime(format)

@application.context_processor
def inject_current_year():
    """Передает текущий год во все шаблоны."""
    return {'current_year': datetime.now(timezone.utc).year}

# Импортируем и регистрируем Blueprints в конце файла, чтобы избежать циклических импортов
from .auth import auth_bp
from .blueprints.main_routes import main_routes
from .blueprints.parsing_routes import parsing_routes
from .blueprints.page_analyzer_routes import page_analyzer_routes
from .blueprints.ai_routes import ai_routes
from .blueprints.api_routes import api_routes

application.register_blueprint(auth_bp, url_prefix='/auth')
application.register_blueprint(main_routes)
application.register_blueprint(parsing_routes)
application.register_blueprint(page_analyzer_routes)
application.register_blueprint(ai_routes)
application.register_blueprint(api_routes, url_prefix='/api')

from . import models # Убедимся, что модели загружены
```

После создания этих файлов и обновления основного приложения, функциональность будет разделена на логические блоки в соответствии с лучшими практиками Flask-разработки.