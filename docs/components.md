## Основные компоненты

### `app/__init__.py`

**Назначение:** Инициализация Flask-приложения и регистрация всех модулей.

**Ключевые функции:**
- Создание экземпляра `Flask`
- Инициализация расширений:
  - **Flask-Login** — управление сессиями пользователей
  - **Flask-Mail** — отправка email
  - **Flask-Caching** — кеширование данных
- Регистрация 11 blueprints (модульные маршруты)
- Определение кастомных фильтров Jinja2
- Внедрение контекстных процессоров

---

### `app/models.py` — Active Record Pattern

**Назначение:** Модели данных с бизнес-логикой (1,909 строк, 98 классов).

**Основные модели:**
- `User` — пользователь с лимитами и ролями
- `Project` — проект парсинга
- `QueryGroup`, `Query` — группы запросов
- `ParsingVariant` — варианты парсинга (SE + регион + устройство)
- `ParsingPositionResult` — результаты позиций
- `SearchEngine`, `SearchType`, `Device` — справочники
- `YandexRegion`, `Location` — география

**Общие методы:**
- `create()` — создание записи
- `get_by_id()` — получение по ID
- `update()` — обновление
- `delete()` — удаление
- Специфичные методы для каждой модели

---

### `app/blueprints/` — Модульные маршруты (11 файлов)

#### `main_routes.py`

**Основные маршруты:**
- `/` — главная страница
- `/show-results` — отображение результатов
- `/get-balance` — баланс XmlRiver
- Импорт локаций и регионов

#### `parsing_routes.py`

**Маршруты парсинга (старая система):**
- `/run` — запуск быстрой проверки позиций
- `/status` — статус парсинга
- `/download-session-results/<session_id>` — скачивание результатов
- `/delete-session/<session_id>` — удаление сессии
- `/estimate-limits` — оценка лимитов

#### `project_routes.py`

**Управление проектами (новая система):**
- `/projects` — список проектов
- `/projects/create` — создание проекта
- `/projects/<id>` — просмотр/редактирование
- `/projects/<id>/delete` — удаление проекта

#### `top_sites_routes.py`

**Выгрузка ТОП-10 сайтов:**
- `/top-sites` — страница модуля
- `/start-top-sites-parsing` — запуск задачи
- `/download-top-sites/<task_id>` — скачивание результатов
- `/delete-top-sites/<task_id>` — удаление задачи

#### `page_analyzer_routes.py`

**Анализатор страниц:**
- `/page-analyzer` — страница анализатора
- `/analyze-pages` — запуск анализа
- `/analysis-status/<task_id>` — статус анализа
- `/download-analysis/<task_id>` — скачивание результатов
- `/delete-analysis/<task_id>` — удаление задачи

#### `ai_routes.py`

**AI функциональность:**
- `/ai` — страница AI-ассистента
- `/article-generator` — генератор статей
- `/ask-ai` — отправка запроса AI
- `/ai-status/<task_id>` — статус AI-задачи
- `/delete-ai-task/<task_id>` — удаление задачи
- `/download-ai-task/<task_id>` — скачивание результатов

#### `api_routes.py`

**REST API:**
- `/api/locations` — локации Google (с пагинацией)
- `/api/yandex-regions` — регионы Яндекса (с пагинацией)
- Другие API эндпоинты

#### `reports_routes.py`

**Отчеты:**
- `/api/reports/...` — генерация отчетов

#### `settings_routes.py`

**Настройки:**
- `/settings` — глобальные настройки приложения

#### `cluster_editor_routes.py`

**Редактор кластеров:**
- `/cluster-editor` — интерфейс редактирования
- Управление кластерами запросов

---

### Дополнительные модули

#### `app/positions_parsing/` — Парсинг позиций (новая система)

**Назначение:** Модуль для работы с проектами и вариантами парсинга.

**Файлы:**
- `routes.py` — маршруты (`/positions/*`)
- Бизнес-логика для новой системы проектов

#### `app/clustering/` — Кластеризация запросов

**Назначение:** Hard-кластеризация по SERP-сходству.

**Файлы:**
- `clustering_routes.py` — маршруты
- Алгоритмы кластеризации
- Сравнение ТОП-10 URL

#### `app/text_tor/` — Генератор ТЗ

**Назначение:** Создание технических заданий для текстов.

**Файлы:**
- `routes.py` — маршруты
- Генерация брифов

#### `app/redirect_checker/` — Проверка редиректов

**Назначение:** Анализ цепочек редиректов URL.

**Файлы:**
- `routes.py` — маршруты
- Логика проверки редиректов

---
156: 
157: ### `app/http_status_checker/` — Проверка статусов HTTP
158: 
159: **Назначение:** Массовая проверка HTTP-статусов URL.
160: 
161: **Файлы:**
162: - `routes.py` — маршруты (`/http-status-checker`)
163: - Логика проверки с защитой от SSRF
164: 
165: **Маршруты:**
166: - `/http-status-checker` — интерфейс проверки
167: - `/check-http-status` — API для проверки
168: - `/download-http-status-results` — скачивание результатов
169: 
170: ---

### `app/parsing.py`

**Назначение:** Управление процессами парсинга (старая система).

**Ключевые функции:**
- `run_parsing_in_thread()` — запуск парсинга в отдельном потоке
- `run_top_sites_parsing_thread()` — парсинг ТОП-10 в потоке
- `parsing_status` — глобальный словарь для отслеживания статуса

---

### `app/xmlriver_client.py`

**Назначение:** Клиент для работы с XmlRiver API (17,632 байт).

**Ключевые функции:**
- `get_live_search_position_looped()` — Yandex Live Search
- `get_google_position_looped()` — Google Search
- `get_position_and_url_single_page()` — Yandex Search API
- Обработка ошибок и retry-логика

---

### `app/page_analyzer_thread.py`

**Назначение:** Асинхронный анализ веб-страниц.

**Ключевые функции:**
- `start_analysis()` — запуск анализа URL в потоке
- `analysis_status` — словарь для отслеживания прогресса

---

### `app/ai.py` и `app/ai_thread.py`

**Назначение:** Взаимодействие с DeepSeek API.

**Ключевые классы:**
- `DeepSeekService` — отправка запросов к OpenRouter
- Асинхронная обработка AI задач

---

### `app/db/` — Работа с базой данных

**Файлы:**
- `database.py` — основное подключение
- `page_analyzer_db.py` — функции для анализатора
- `ai_db.py` — функции для AI модуля
- `settings_db.py` — управление настройками

---

### `app/auth.py`

**Назначение:** Аутентификация и авторизация (10,998 байт).

**Основные маршруты:**
- `/auth/login` — вход в систему
- `/auth/register` — регистрация
- `/auth/logout` — выход
- `/auth/forgot-password` — восстановление пароля
- `/auth/reset-password` — сброс пароля

**Функции:**
- Хеширование паролей (Werkzeug)
- Генерация токенов восстановления
- Flask-Login integration

---

### `app/config.py`

**Назначение:** Конфигурация приложения.

**Классы:**
- `Config` — основная конфигурация
- `MailConfig` — настройки email
- `XmlRiverConfig` — настройки API
- `CacheConfig` — настройки кеширования

**Источники конфигурации:**
- Файл `.env`
- База данных (таблица `settings`)

---

### Вспомогательные модули

- `app/utils.py` — вспомогательные функции
- `app/region_utils.py` — утилиты для работы с регионами
- `app/parsing_utils.py` — утилиты для парсинга
- `app/keyword_frequency_parser.py` — анализ частотности ключевых слов (17,854 байт)

---

### Статические файлы и шаблоны

**`static/`**
- `css/` — скомпилированный Tailwind CSS
- `js/` — клиентские скрипты

**`templates/`** (29 файлов)
- `layout.html` — базовый шаблон
- `login.html`, `register.html` — аутентификация
- `home.html` — главная страница
- `projects/` — шаблоны проектов
- `components/` — переиспользуемые компоненты
- и другие...