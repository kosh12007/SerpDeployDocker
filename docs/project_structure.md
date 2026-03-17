## Структура проекта

```
serp/
├── app/                          # Основной код приложения (25 файлов + 8 подпапок)
│   ├── __init__.py              # Инициализация Flask (120 строк)
│   ├── auth.py                  # Аутентификация (10,998 байт)
│   ├── config.py                # Конфигурация приложения
│   ├── models.py                # Модели данных (1,909 строк, 98 моделей)
│   ├── parsing.py               # Логика парсинга (старая система)
│   ├── xmlriver_client.py       # Клиент XmlRiver API (17,632 байт)
│   │
│   ├── blueprints/              # Модульные маршруты (11 файлов)
│   │   ├── __init__.py
│   │   ├── main_routes.py       # Основные маршруты приложения
│   │   ├── parsing_routes.py    # Маршруты парсинга (старая система)
│   │   ├── project_routes.py    # Управление проектами (новая система)
│   │   ├── top_sites_routes.py  # Выгрузка ТОП-10 сайтов
│   │   ├── page_analyzer_routes.py  # Анализатор страниц
│   │   ├── ai_routes.py         # AI-функциональность (DeepSeek)
│   │   ├── api_routes.py        # REST API эндпоинты
│   │   ├── reports_routes.py    # Генерация отчетов
│   │   ├── settings_routes.py   # Глобальные настройки
│   │   └── cluster_editor_routes.py  # Редактор кластеров
│   │
│   ├── db/                      # Работа с базой данных (10 файлов)
│   │   ├── database.py          # Основное подключение к БД
│   │   ├── page_analyzer_db.py  # Функции для анализатора страниц
│   │   ├── ai_db.py             # Функции для AI модуля
│   │   ├── settings_db.py       # Управление настройками
│   │   └── ...
│   │
│   ├── positions_parsing/       # Модуль парсинга позиций (14 файлов)
│   │   ├── routes.py            # Маршруты новой системы проектов
│   │   └── ...
│   │
│   ├── clustering/              # Кластеризация запросов (4 файла)
│   │   ├── clustering_routes.py # Маршруты кластеризации
│   │   └── ...
│   │
│   ├── text_tor/                # Генератор ТЗ для текстов (2 файла)
│   │   ├── routes.py
│   │   └── ...
│   │
│   ├── redirect_checker/        # Проверка редиректов (2 файла)
│   │   ├── routes.py
│   │   └── ...
│   │
│   ├── http_status_checker/     # Модуль проверки статусов HTTP (2 файла)
│   │   ├── routes.py            # Маршруты и логика проверки
│   │   └── ...
│   │
│   ├── upgrade/                 # Утилиты обновления (6 файлов)
│   │
│   ├── page_analyzer.py         # Логика анализатора страниц
│   ├── page_analyzer_thread.py  # Потоковая обработка анализа
│   ├── ai.py                    # Сервис DeepSeek
│   ├── ai_thread.py             # Потоковая обработка AI
│   ├── top_sites_parser_thread.py  # Потоковая обработка ТОП-10
│   ├── keyword_frequency_parser.py  # Анализ частотности (17,854 байт)
│   ├── utils.py                 # Вспомогательные функции
│   ├── region_utils.py          # Утилиты для регионов
│   └── parsing_utils.py         # Утилиты для парсинга
│
├── static/                      # Статические файлы (36 файлов)
│   ├── css/                     # Скомпилированный Tailwind CSS
│   │   ├── main.css             # Основные стили
│   │   ├── theme-light.css      # Светлая тема
│   │   ├── theme-dark.css       # Темная тема
│   │   ├── input-*.css          # Исходники для Tailwind
│   │   └── ...
│   ├── js/                      # JavaScript файлы
│   │   ├── modal.js             # Модальные окна
│   │   └── ...
│   └── images/                  # Изображения
│
├── templates/                   # HTML шаблоны (29 файлов)
│   ├── layout.html              # Базовый шаблон
│   ├── home.html                # Главная страница
│   ├── index.html               # Быстрая проверка (старая система)
│   ├── login.html, register.html  # Аутентификация
│   ├── forgot-password.html, reset-password.html
│   ├── results.html             # Результаты парсинга
│   ├── top_sites.html           # ТОП-10 сайтов
│   ├── page_analyzer.html       # Анализатор страниц
│   ├── ai.html                  # AI-ассистент
│   ├── article_generator.html   # Генератор статей
│   ├── clustering.html          # Кластеризация
│   ├── cluster_editor.html      # Редактор кластеров
│   ├── redirect_checker.html    # Проверка редиректов
│   ├── create_text_tor.html     # Генератор ТЗ
│   ├── settings.html            # Настройки
│   ├── keyword_frequency.html   # Частотность ключевых слов
│   ├── projects/                # Шаблоны проектов (4 файла)
│   │   ├── index.html           # Список проектов
│   │   ├── view.html            # Просмотр проекта
│   │   └── ...
│   ├── components/              # Переиспользуемые компоненты (3 файла)
│   └── email/                   # Email шаблоны (1 файл)
│
├── docs/                        # Документация (13 файлов)
│   ├── README.md                # Оглавление
│   ├── introduction.md          # Введение
│   ├── tech_stack.md            # Технологический стек
│   ├── project_structure.md     # Структура проекта
│   ├── installation.md          # Установка и запуск
│   ├── components.md            # Основные компоненты
│   ├── database.md              # Схема базы данных
│   ├── api.md                   # API эндпоинты
│   ├── ai_assistant.md          # AI ассистент
│   ├── clustering_spec.md       # Спецификация кластеризации
│   ├── modal_system_documentation.md  # Модальные окна (38,781 байт)
│   ├── layout_functions.md      # Функции шаблона
│   └── project_analysis.md      # Комплексный анализ проекта
│
├── migrations/                  # SQL миграции (12 файлов)
│   ├── 000_create_migrations_table.sql
│   ├── add_limits_to_users.sql
│   ├── add_admin_roles_to_users.sql
│   ├── create_parsing_positions_sessions.sql
│   └── ...
│
├── tests/                       # Тесты (9 файлов)
│   ├── test_main_routes.py
│   ├── test_parsing_routes.py
│   ├── test_ai_routes.py
│   ├── test_page_analyzer_routes.py
│   ├── test_top_sites_routes.py
│   ├── test_api_routes.py
│   ├── test_positions.py
│   ├── test_top_sites.py
│   └── test_clustering_fix.py
│
├── logs/                        # Файлы логов (32 файла)
│   ├── main_script.log
│   ├── __init__.py.log
│   └── ...
│
├── .vscode/                     # Настройки VS Code
├── .kilocode/                   # Настройки Kilocode AI
├── __pycache__/                 # Python кеш
├── node_modules/                # Node.js зависимости
│
├── main.py                      # Точка входа приложения (473 строки)
├── passenger_wsgi.py            # WSGI для Passenger (хостинг)
├── serp.py                      # Дополнительный модуль (190 байт)
│
├── requirements.txt             # Python зависимости (20 пакетов)
├── package.json                 # Node.js зависимости (Tailwind)
├── package-lock.json            # Lockfile Node.js
├── tailwind.config.js           # Конфигурация Tailwind CSS
├── postcss.config.js            # Конфигурация PostCSS
│
├── .env                         # Переменные окружения (2,098 байт)
├── serp.code-workspace          # Workspace для VS Code
│
├── install_dependencies.bat     # Скрипт установки зависимостей
├── compile_styles.bat           # Скрипт компиляции CSS
├── create_backup_serp.bat       # Скрипт создания бэкапа
│
├── import_locations.py          # Импорт локаций Google
├── import_countries.py          # Импорт стран
├── page_analyzer.py             # Standalone анализатор
├── page_analyzer_thread.py      # Standalone потоковый анализатор
├── top_sites_parser.py          # Standalone парсер ТОП-10
│
├── countries.xlsx               # Справочник стран
├── example_windows-1251.csv     # Пример файла
├── geo (1).csv                  # Локации Google (7.4 МБ)
│
└── *.sql                        # SQL файлы (23 файла)
    ├── serp.sql                 # Основная схема БД
    ├── SerpRegions.sql          # Регионы (9.7 МБ)
    ├── yandex_regions.sql       # Регионы Яндекса
    ├── rollback_and_create_new_tables.sql
    └── ...
```

## Ключевые директории

- **`app/`** — основной код приложения (MVC архитектура)
- **`app/blueprints/`** — модульные маршруты (11 blueprints)
- **`app/db/`** — работа с базой данных
- **`static/`** — статика (CSS, JS, изображения)
- **`templates/`** — HTML шаблоны (Jinja2)
- **`docs/`** — документация проекта
- **`migrations/`** — SQL миграции
- **`tests/`** — автотесты (pytest)
- **`logs/`** — логи приложения

## Важные файлы

- **`main.py`** — точка входа в приложение
- **`app/models.py`** — все модели данных (Active Record)
- **`app/__init__.py`** — инициализация Flask-приложения
- **`requirements.txt`** — Python зависимости
- **`.env`** — конфигурация (подключение к БД, API ключи)