"""
Text analyzer routes blueprint for SERP bot application.

Contains routes for:
- Text analyzer page
- Analyzing text content from URL or direct input
"""

from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required, current_user
import os
import logging
import json
import io
import pandas as pd
from ..text_analyzer.text_analyzer import analyze_url_or_text
from ..db_config import LOGGING_ENABLED

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "text_analyzer_routes.log")
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

text_analyzer_routes = Blueprint("text_analyzer", __name__)


@text_analyzer_routes.route("/text-analyzer")
# Разкомментируй следующую строку если нужно чтобы функция была доступна только для авторизованных пользователей
# @login_required
def text_analyzer():
    """Отображает страницу анализатора текста."""
    return render_template("text_analyzer.html")


@text_analyzer_routes.route("/analyze-text", methods=["POST"])
# Разкомментируй следующую строку если нужно чтобы функция была доступна только для авторизованных пользователей
# @login_required
def analyze_text():
    """Обрабатывает запрос на анализ текста или URL."""
    try:
        data = request.get_json()
        text_input = data.get("text_input", "").strip()
        input_type = data.get("input_type", "text")  # 'url' или 'text'

        if not text_input:
            return jsonify({"error": "Текст или URL не указаны"}), 400

        # Определяем, является ли ввод URL или текстом
        is_url = input_type == "url"

        # Выполняем анализ
        result = analyze_url_or_text(text_input, is_url=is_url)

        if "error" in result:
            return jsonify(result), 400

        return jsonify({"success": True, "data": result})

    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(f"Ошибка при анализе текста: {e}", exc_info=True)
        return jsonify({"error": "Произошла ошибка при анализе текста"}), 500


@text_analyzer_routes.route("/download-text-results", methods=["POST"])
def download_text_results():
    """Формирует и отдает файл с результатами анализа текста."""
    results_data_str = request.form.get("results_data")
    file_format = request.args.get("format", "xlsx")
    encoding = request.args.get("encoding", "utf-8")

    if not results_data_str:
        return "Нет данных для скачивания", 400

    try:
        data = json.loads(results_data_str)
    except json.JSONDecodeError:
        return "Ошибка в формате данных", 400

    # 1. Основные метрики
    main_metrics_records = [
        {
            "Метрика": "Символов (с пробелами)",
            "Значение": data.get("chars_with_spaces"),
        },
        {
            "Метрика": "Символов (без пробелов)",
            "Значение": data.get("chars_without_spaces"),
        },
        {"Метрика": "Всего слов", "Значение": data.get("word_count")},
        {"Метрика": "Уникальных слов", "Значение": data.get("unique_word_count")},
        {"Метрика": "Водность (%)", "Значение": data.get("water_percentage")},
        {"Метрика": "Классическая тошнота", "Значение": data.get("classic_nausea")},
        {
            "Метрика": "Академическая тошнота (%)",
            "Значение": data.get("academic_nausea"),
        },
        {"Метрика": "Заспамленность (%)", "Значение": data.get("spam_score")},
    ]
    df_main = pd.DataFrame(main_metrics_records)

    # 2. N-граммы
    top_ngrams = data.get("top_ngrams", {})
    df_1gram = pd.DataFrame(top_ngrams.get("1_word", []), columns=["Слово", "Частота"])
    df_2gram = pd.DataFrame(
        top_ngrams.get("2_words", []), columns=["Фраза (2 слова)", "Частота"]
    )
    df_3gram = pd.DataFrame(
        top_ngrams.get("3_words", []), columns=["Фраза (3 слова)", "Частота"]
    )
    df_stop = pd.DataFrame(
        top_ngrams.get("stop_words", []), columns=["Стоп-слово", "Частота"]
    )

    if file_format == "xlsx":
        try:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_main.to_excel(writer, index=False, sheet_name="Общие метрики")
                df_1gram.to_excel(writer, index=False, sheet_name="1-граммы")
                df_2gram.to_excel(writer, index=False, sheet_name="2-граммы")
                df_3gram.to_excel(writer, index=False, sheet_name="3-граммы")
                df_stop.to_excel(writer, index=False, sheet_name="Стоп-слова")
            output.seek(0)
            return Response(
                output,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": "attachment;filename=text_analysis_results.xlsx"
                },
            )
        except Exception as e:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка при создании XLSX для анализа текста: {e}", exc_info=True
                )
            return "Не удалось сгенерировать XLSX файл.", 500

    elif file_format == "csv" or file_format == "txt":
        # Формируем полный отчет со всеми данными
        report_parts = ["--- ОБЩИЕ МЕТРИКИ ---", df_main.to_csv(index=False, sep=";")]

        report_parts.append("\n--- ВСЕ СЛОВА (1 слово) ---")
        report_parts.append(df_1gram.to_csv(index=False, sep=";"))

        report_parts.append("\n--- ВСЕ ФРАЗЫ (2 слова) ---")
        report_parts.append(df_2gram.to_csv(index=False, sep=";"))

        report_parts.append("\n--- ВСЕ ФРАЗЫ (3 слова) ---")
        report_parts.append(df_3gram.to_csv(index=False, sep=";"))

        report_parts.append("\n--- СТОП-СЛОВА ---")
        report_parts.append(df_stop.to_csv(index=False, sep=";"))

        full_report = "\n".join(report_parts)

        if file_format == "csv":
            if encoding == "windows-1251":
                encoded_data = full_report.encode("windows-1251", errors="replace")
            else:
                encoded_data = full_report.encode("utf-8-sig")

            mimetype = f"text/csv; charset={encoding}"
            filename = f"text_analysis_results_{encoding}.csv"
        else:
            encoded_data = full_report.encode("utf-8")
            mimetype = "text/plain"
            filename = "text_analysis_results.txt"

        return Response(
            encoded_data,
            mimetype=mimetype,
            headers={"Content-Disposition": f'attachment;filename="{filename}"'},
        )

    return "Неверный формат файла", 400
