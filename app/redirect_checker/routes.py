import pandas as pd
import io
import logging
import os
from flask import Blueprint, render_template, request, jsonify, Response
from app.db_config import LOGGING_ENABLED
from urllib.parse import urlparse, urljoin
import requests
import json

# Создаем Blueprint для проверки редиректов
redirect_checker_bp = Blueprint("redirect_checker", __name__)

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "redirect_checker.log")
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
    if LOGGING_ENABLED:
        logger.info(f"Логгер для {__name__} настроен.")
# --- Конец настройки логгера ---


def generate_urls(base_url):
    """Генерирует список URL для проверки на основе введенного URL."""
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    parsed_url = urlparse(base_url)
    scheme = parsed_url.scheme
    netloc = parsed_url.netloc
    path = parsed_url.path

    # Удаляем 'www.' если оно есть
    if netloc.startswith("www."):
        domain_without_www = netloc[4:]
    else:
        domain_without_www = netloc
        netloc = "www." + netloc

    urls_to_check = [
        f"https://{domain_without_www}",
        f"http://{domain_without_www}",
        f"https://{netloc}",
        f"http://{netloc}",
        f"https://{domain_without_www}///",
        f"http://{domain_without_www}///",
        f"https://{netloc}///",
        f"http://{netloc}///",
    ]

    # Добавляем URL с путем, если он есть
    if path and path != "/":
        # Вариант с последним символом в верхнем регистре
        if path.endswith("/"):
            # Если путь заканчивается на /, берем символ перед ним
            if len(path) > 1:
                path_with_uppercase = path[:-2] + path[-2].upper() + "/"
                urls_to_check.append(
                    f"{scheme}://{parsed_url.netloc}{path_with_uppercase}"
                )
        else:
            path_with_uppercase = path[:-1] + path[-1].upper()
            urls_to_check.append(f"{scheme}://{parsed_url.netloc}{path_with_uppercase}")

    # Убираем дубликаты
    return sorted(list(set(urls_to_check)))


def check_redirect(url):
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

                # Это ключевой трюк: вручную задаем URL для отправки, обходя нормализацию requests
                # Мы не используем session.send(prepared_req), а создаем новый запрос
                # с помощью urllib3 через сессию requests, но передаем ему нужный нам путь.
                # Однако, requests сам не позволяет легко подменить путь в PreparedRequest.
                # Поэтому используем сессию requests, но с кастомной логикой редиректа.

                # Вместо session.send, будем использовать requests.get с allow_redirects=False
                # и вручную обрабатывать редиректы.
                # requests.get нормализует URL при подготовке, но если мы будем использовать
                # urllib3 напрямую через requests.adapters, можно обойти это.
                # Но проще и надежнее использовать session.get с allow_redirects=False
                # и вручную следить за редиректами, контролируя URL.

                # Попробуем другой подход: используем session, но обходим нормализацию
                # на уровне подготовки запроса.

                # requests не позволяет легко изменить path в PreparedRequest после его создания.
                # Но мы можем использовать urllib3 напрямую через адаптеры сессии.
                # Однако, это слишком сложно.

                # Простое и эффективное решение: использовать requests.get с allow_redirects=False
                # и вручную обработать редиректы. Но как передать "грязный" URL?

                # Единственный способ обойти нормализацию в requests - это использовать
                # сессию и изменить _pool_manager напрямую, что не рекомендуется.

                # Альтернатива: использовать requests с хитростью. Подготовим запрос,
                # а затем вручную заменим путь в URL перед отправкой через urllib3.
                # Но это тоже хрупко.

                # Правильный способ: использовать requests, но манипулировать URL так,
                # чтобы он не нормализовался. requests нормализует путь, но не параметры.
                # Однако, если в пути /// это часть пути, а не параметры, нормализация произойдет.

                # Самое простое: использовать requests, но с сессией и allow_redirects=False
                # и вручную обрабатывать редиректы. requests.get(url) сам нормализует URL.

                # Обходной путь: использовать urllib3 напрямую, но через сессию requests.
                # Или использовать requests с кастомным TransportAdapter.

                # Попробуем использовать requests с allow_redirects=False и вручную
                # обрабатывать редиректы, но с учетом нормализации.

                # requests.get(url, allow_redirects=False) НОРМАЛИЗУЕТ url при подготовке!
                # Поэтому даже первый запрос будет неправильным.

                # Решение: использовать requests, но обойти нормализацию на уровне сессии.
                # requests.Session() позволяет подменить адаптер.

                # Используем кастомный Transport Adapter для обхода нормализации.
                # import urllib3

                # Создаем кастомный PoolManager, который не нормализует URL.
                # Это возможно, но требует знаний urllib3.
                # requests использует urllib3.PoolManager.
                # urllib3.poolmanager.PoolManager.connection_from_url() нормализует URL.

                # Лучший способ: использовать urllib3 напрямую, но обернуть в логику requests.

                # Однако, самый простой и надежный способ, который не ломает requests:
                # Подготовить запрос, подменить путь, а потом отправить.
                # Но PreparedRequest.url нельзя просто так изменить.

                # Решение: использовать requests с сессией и кастомным адаптером.
                # urllib3.util.retry.Retry не поможет напрямую.

                # Вот рабочий способ: использовать requests, но с хитростью.
                # requests.session().get() также нормализует.

                # Попробуем использовать urllib3 напрямую, но через requests.
                # requests.packages.urllib3.PoolManager

                # Импортируем urllib3 напрямую.
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


@redirect_checker_bp.route("/generate-url-list", methods=["POST"])
def generate_url_list():
    """Генерирует список URL для проверки."""
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL не указан"}), 400

    urls = generate_urls(url)
    return jsonify({"urls": urls})


@redirect_checker_bp.route("/check-redirects", methods=["GET", "POST"])
def check_redirects_page():
    """Отображает страницу и обрабатывает проверку редиректов."""
    if request.method == "POST":
        data = request.get_json()
        urls = data.get("urls")
        if not urls or not isinstance(urls, list):
            return (
                jsonify({"error": "Список URL не указан или имеет неверный формат"}),
                400,
            )

        results = {}
        for u in urls:
            results[u] = check_redirect(u)

        return jsonify(results)

    return render_template("redirect_checker.html")


@redirect_checker_bp.route("/download-redirect-results", methods=["POST"])
def download_redirect_results():
    """Формирует и отдает файл с результатами проверки редиректов."""
    results_data_str = request.form.get("results_data")
    file_format = request.args.get("format", "xlsx")
    encoding = request.args.get("encoding", "utf-8")

    if LOGGING_ENABLED:
        logger.debug(f"Запрошен формат: {file_format}, кодировка: {encoding}")
        logger.debug(
            f"Получены сырые данные: {results_data_str[:500]}..."
        )  # Логируем только часть данных

    if not results_data_str:
        if LOGGING_ENABLED:
            logger.warning("Нет данных для скачивания (results_data_str is empty).")
        return "Нет данных для скачивания", 400

    try:
        results_data = json.loads(results_data_str)
        if LOGGING_ENABLED:
            logger.debug("Данные JSON успешно распарсены.")
    except json.JSONDecodeError as e:
        if LOGGING_ENABLED:
            logger.error(f"Ошибка декодирования JSON: {e}", exc_info=True)
        return "Ошибка в формате данных", 400

    records = []
    index = 1
    for original_url, history in results_data.items():
        if history:
            # Для корректного отчета, мы берем ПЕРВЫЙ статус.
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

    if LOGGING_ENABLED:
        logger.debug(
            f"Сформированы записи для DataFrame: {records[:5]}"
        )  # Логируем первые 5 записей

    try:
        df = pd.DataFrame(records)
        if LOGGING_ENABLED:
            buffer = io.StringIO()
            df.info(buf=buffer)
            logger.debug(f"Информация о DataFrame:\n{buffer.getvalue()}")
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(f"Ошибка при создании DataFrame: {e}", exc_info=True)
        return "Ошибка при обработке данных для отчета", 500

    if file_format == "xlsx":
        try:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Redirects")
            output.seek(0)
            if LOGGING_ENABLED:
                logger.info("XLSX файл успешно создан.")
            return Response(
                output,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": "attachment;filename=redirect_results.xlsx"
                },
            )
        except Exception as e:
            if LOGGING_ENABLED:
                logger.error(f"Ошибка при создании XLSX файла: {e}", exc_info=True)
            return "Не удалось сгенерировать XLSX файл.", 500
    elif file_format == "csv":
        # Pandas to_csv с параметром encoding может работать не так, как ожидается,
        # поэтому для надежности кодируем вручную.
        csv_data = df.to_csv(index=False, sep=";")

        # Кодируем байты в зависимости от выбранной кодировки
        if encoding == "windows-1251":
            encoded_data = csv_data.encode("windows-1251", errors="replace")
        else:  # utf-8 по умолчанию
            # Используем 'utf-8-sig', чтобы добавить BOM для лучшей совместимости с Excel
            encoded_data = csv_data.encode("utf-8-sig")

        mimetype = f"text/csv; charset={encoding}"
        filename = f"redirect_results_{encoding}.csv"

        return Response(
            encoded_data,
            mimetype=mimetype,
            headers={"Content-Disposition": f'attachment;filename="{filename}"'},
        )
    elif file_format == "txt":
        txt_data = df.to_string(index=False)
        mimetype = "text/plain"
        filename = "redirect_results.txt"
        return Response(
            txt_data,
            mimetype=mimetype,
            headers={"Content-Disposition": f"attachment;filename={filename}"},
        )

    return "Неверный формат файла", 400
