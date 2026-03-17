# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv

load_dotenv()

# Загрузка конфигурации базы данных из .env файла
DB_CONFIG = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME')
}

LOGGING_ENABLED = os.getenv('LOGGING_ENABLED', 'False').lower() in ('true', '1', 't')