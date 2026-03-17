import pandas as pd
import io
import logging
import os
import json
from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required
from app.db_config import LOGGING_ENABLED
from app.db.settings_db import get_setting
from urllib.parse import urlparse, urljoin
import requests

# Создаем Blueprint для проверки HTTP статусов
http_status_checker_bp = Blueprint("http_status_checker", __name__)

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "http_status_checker.log")
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
else:
    logger = logging.getLogger(__name__)
# --- Конец настройки логгера ---


def get_max_urls_limit():
    """Получает максимальное количество URL из настроек."""
    try:
        limit = get_setting("MAX_HTTP_STATUS_URLS")
        return int(limit) if limit else 50
    except (ValueError, TypeError):
        return 50


def check_http_status(url):
    """Проверяет редиректы для одного URL и возвращает историю, обходя нормализацию URL."""
    history = []
    max_redirects = 10
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "*/*",
    }

    try:
        # Создаем сессию, чтобы иметь больший контроль
        with requests.Session() as session:
            # Отключаем автоматические редиректы
            session.max_redirects = 0

            current_url = url
            for _ in range(max_redirects):
                # Используем urllib3 напрямую через requests для отправки "сырого" запроса
                req = requests.Request("GET", current_url, headers=headers)
                prepared_req = req.prepare()
                import urllib3

                # Отключаем предупреждения urllib3, если они есть
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

                # Создаем менеджер пулов напрямую, чтобы обойти нормализацию
                http_pool_manager = urllib3.PoolManager(
                    timeout=urllib3.Timeout(connect=5.0, read=10.0),
                    retries=False,  # Редиректы будем обрабатывать вручную
                )

                # Парсим URL
                parsed = urlparse(current_url)
                path_and_query = parsed.path
                if parsed.query:
                    path_and_query += "?" + parsed.query

                # Отправляем запрос напрямую через urllib3, минуя нормализацию requests
                res = http_pool_manager.request(
                    "GET",
                    current_url,
                    fields=None,  # Не используем fields, так как это GET
                    headers=headers,
                    redirect=False,  # Редиректы обрабатываем вручную
                    preload_content=False,
                )

                status_code = res.status
                location = res.headers.get("Location")
                final_url = res.geturl()  # URL, по которому был получен ответ

                history.append(
                    {
                        "url": current_url,  # Записываем оригинальный URL, который отправили
                        "status_code": status_code,
                        "final_url": location,
                    }
                )

                res.release_conn()  # Важно: освобождаем соединение

                if 300 <= status_code < 400 and location:
                    # Следуем по редиректу, используя urljoin для корректного построения URL
                    current_url = urljoin(current_url, location)
                else:
                    # Не редирект или нет заголовка Location, выходим
                    break
            else:
                # Если цикл завершился по max_redirects, добавляем сообщение
                history.append(
                    {
                        "url": current_url,
                        "status_code": "Слишком много редиректов",
                        "final_url": None,
                    }
                )

    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(f"Ошибка при проверке URL {url}: {e}", exc_info=True)
        return [{"url": url, "status_code": f"Ошибка: {e}", "final_url": None}]

    return history


@http_status_checker_bp.route("/http-status-checker", methods=["GET"])
# Разкомментировать если нужено чтобы авторизация была обязательной
# @login_required
def http_status_checker_page():
    """Отображает страницу проверки HTTP статусов."""
    max_urls = get_max_urls_limit()
    return render_template("http_status_checker.html", max_urls=max_urls)


@http_status_checker_bp.route("/check-http-status", methods=["POST"])
# Разкомментировать если нужено чтобы авторизация была обязательной
# @login_required
def check_http_status_api():
    """API для проверки списка URL. Возвращает результаты в формате словаря."""
    data = request.get_json()
    urls = data.get("urls", [])

    if not urls or not isinstance(urls, list):
        return jsonify({"error": "Список URL не указан или имеет неверный формат"}), 400

    # Проверяем лимит
    max_urls = get_max_urls_limit()
    if len(urls) > max_urls:
        return (
            jsonify(
                {
                    "error": f"Превышен лимит URL. Максимум: {max_urls}, получено: {len(urls)}"
                }
            ),
            400,
        )

    # Фильтруем и очищаем URL
    urls = [u.strip() for u in urls if u.strip()]

    # --- SSRF Protection ---
    import ipaddress
    import socket

    safe_urls = []

    for u in urls:
        try:
            # Добавляем протокол для парсинга
            parsed_u = u if u.startswith(("http://", "https://")) else "https://" + u
            parsed = urlparse(parsed_u)
            hostname = parsed.hostname
            if not hostname:
                # Если hostname пустой, пропускаем
                continue

            # Резолвим IP
            ip = socket.gethostbyname(hostname)
            ip_addr = ipaddress.ip_address(ip)

            # Проверяем на принадлежность к приватным сетям
            if (
                ip_addr.is_private
                or ip_addr.is_loopback
                or ip_addr.is_reserved
                or ip_addr.is_link_local
            ):
                if LOGGING_ENABLED:
                    logger.warning(
                        f"Blocked SSRF attempt for URL: {u} (Resolved to: {ip})"
                    )
                continue

            safe_urls.append(u)

        except Exception as e:
            if LOGGING_ENABLED:
                logger.warning(f"Error validating URL {u}: {e}")
            # В случае ошибки резолва или парсинга, лучше пропустить URL от греха подальше,
            # но для пользовательского опыта можно и оставить, если уверены.
            # Здесь мы пропускаем подозрительные.
            continue

    urls = safe_urls
    # --- End SSRF Protection ---

    if LOGGING_ENABLED:
        logger.info(f"Начало проверки {len(urls)} URL")

    # Возвращаем результаты как словарь {original_url: history}
    results = {}
    for url in urls:
        # Добавляем протокол если его нет (для ключа)
        original_url = (
            url if url.startswith(("http://", "https://")) else "https://" + url
        )
        history = check_http_status(url)
        results[original_url] = history

    if LOGGING_ENABLED:
        logger.info(f"Проверка завершена. Обработано {len(results)} URL")

    return jsonify(results)


@http_status_checker_bp.route("/download-http-status-results", methods=["POST"])
# Разкомментировать если нужено чтобы авторизация была обязательной
# @login_required
def download_http_status_results():
    """Формирует и отдает файл с результатами проверки HTTP статусов."""
    results_data_str = request.form.get("results_data")
    file_format = request.args.get("format", "xlsx")
    encoding = request.args.get("encoding", "utf-8")

    if LOGGING_ENABLED:
        logger.debug(f"Запрошен формат: {file_format}, кодировка: {encoding}")

    if not results_data_str:
        if LOGGING_ENABLED:
            logger.warning("Нет данных для скачивания")
        return "Нет данных для скачивания", 400

    try:
        results_data = json.loads(results_data_str)
    except json.JSONDecodeError as e:
        if LOGGING_ENABLED:
            logger.error(f"Ошибка декодирования JSON: {e}")
        return "Ошибка в формате данных", 400

    # Формируем записи для DataFrame (формат как в redirect_checker)
    records = []
    index = 1
    for original_url, history in results_data.items():
        if history:
            # Берем первый статус (исходный URL)
            status_code = str(history[0].get("status_code", "Ошибка"))

            if len(history) > 1:
                # Цепочка показывает все шаги, включая финальный статус
                chain = " > ".join(str(h.get("status_code", "")) for h in history)
                # Конечный URL - это URL последнего ответа
                final_url = history[-1].get("url", "")
            else:
                chain = ""
                final_url = ""
        else:
            status_code = "Ошибка"
            chain = ""
            final_url = "Не удалось проверить"

        records.append(
            {
                "№": index,
                "URL": original_url,
                "HTTP-ответ": status_code,
                "Цепочка": chain,
                "Конечный URL": final_url,
            }
        )
        index += 1

    try:
        df = pd.DataFrame(records)
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(f"Ошибка при создании DataFrame: {e}")
        return "Ошибка при обработке данных", 500

    if file_format == "xlsx":
        try:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="HTTP Status")
            output.seek(0)
            if LOGGING_ENABLED:
                logger.info("XLSX файл успешно создан")
            return Response(
                output,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": "attachment;filename=http_status_results.xlsx"
                },
            )
        except Exception as e:
            if LOGGING_ENABLED:
                logger.error(f"Ошибка при создании XLSX: {e}")
            return "Не удалось сгенерировать XLSX файл", 500

    elif file_format == "csv":
        csv_data = df.to_csv(index=False, sep=";")

        if encoding == "windows-1251":
            encoded_data = csv_data.encode("windows-1251", errors="replace")
        else:
            encoded_data = csv_data.encode("utf-8-sig")

        mimetype = f"text/csv; charset={encoding}"
        filename = f"http_status_results_{encoding}.csv"

        return Response(
            encoded_data,
            mimetype=mimetype,
            headers={"Content-Disposition": f'attachment;filename="{filename}"'},
        )

    elif file_format == "txt":
        txt_data = df.to_string(index=False)
        return Response(
            txt_data,
            mimetype="text/plain",
            headers={
                "Content-Disposition": "attachment;filename=http_status_results.txt"
            },
        )

    return "Неверный формат файла", 400
