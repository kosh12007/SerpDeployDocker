# Dockerfile для Flask SEO-приложения Serp
# Базовый образ: Python 3.11 slim для минимального размера
FROM python:3.11-slim

# Метаданные образа
LABEL maintainer="seoorbita.ru"
LABEL description="Serp - SEO анализ и мониторинг позиций"

# Переменные окружения для Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Ограничиваем потоки OpenBLAS (важно для numpy/pandas)
    OPENBLAS_NUM_THREADS=1 \
    # Рабочая директория
    APP_DIR=/app

# Установка системных зависимостей
# gcc и pkg-config нужны для сборки mysql-connector и scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    # Очищаем кеш apt для уменьшения размера образа
    && rm -rf /var/lib/apt/lists/*

# Создаём рабочую директорию
WORKDIR /app

# Копируем файл зависимостей первым — используем кеш Docker
# Если requirements.txt не изменился, слой не пересобирается
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Устанавливаем gunicorn для продакшн-запуска
    pip install --no-cache-dir gunicorn==21.2.0

# Создаём директорию для логов
RUN mkdir -p /app/logs

# Копируем исходный код приложения
COPY . .

# Копируем и даём права на выполнение скрипту запуска
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Открываем порт приложения (gunicorn слушает 8000)
EXPOSE 8000

# Точка входа — скрипт, который ждёт MySQL и запускает gunicorn
ENTRYPOINT ["/entrypoint.sh"]
