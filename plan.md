# План тестирования приложения SERP

## 1. Введение

Целью данного плана является обеспечение полного покрытия тестирования для веб-приложения SERP, которое занимается парсингом поисковой выдачи. План включает как автоматизированные, так и ручные тесты для проверки функциональности, безопасности, API и других аспектов приложения.

## 2. Области тестирования

### 2.1. Функциональное тестирование

#### 2.1.1. Аутентификация и авторизация

- [x] Регистрация нового пользователя — `tests/test_auth.py::test_register_success`, `test_register_username_exists`, `test_register_passwords_mismatch`, `test_register_short_password`
- [x] Вход в систему — `tests/test_auth.py::test_login_success`, `test_login_failure`
- [x] Восстановление пароля — `tests/test_ui_functional.py::test_forgot_password_page_loads`; ручной тест `tests/manual_test_cases.md` §1.1 (Ок)
- [x] Сброс пароля по ссылке — `tests/manual_test_cases.md` §1.1 (Ок)
- [x] Выход из системы — `tests/test_auth.py::test_logout`
- [x] Проверка доступа к защищенным страницам без авторизации — `tests/test_security.py::test_dashboard_redirect_without_auth`, `tests/test_ui_functional.py::TestProtectedPages`
- [x] Ролевая модель (администратор, обычный пользователь) — `tests/test_security.py::test_admin_pages_require_admin_role`
- [x] Проверка доступа к ресурсам других пользователей — `tests/test_security.py::test_other_user_data_not_accessible`, `tests/test_projects.py::test_project_detail_access_denied`

#### 2.1.2. Управление проектами

- [x] Создание нового проекта — `tests/test_projects.py::test_create_project_success`, `tests/test_queries.py::QueryManagementTestCase::test_add_queries_to_project_success`
- [x] Редактирование проекта — `tests/test_queries.py::ProjectDetailTestCase::test_project_detail_page`
- [x] Удаление проекта — `tests/test_projects.py::test_delete_project_success`
- [x] Список проектов пользователя — `tests/test_projects.py::test_project_list_authorized`, `tests/test_queries.py::ProjectDetailTestCase::test_api_projects_list`
- [x] Проверка прав доступа к проектам других пользователей — `tests/test_projects.py::test_project_detail_access_denied`
- [x] Валидация данных при создании/редактировании проекта — `tests/test_projects.py::test_create_project_validation_error`, `tests/test_queries.py::ParsingVariantTestCase::test_add_parsing_variant_missing_fields`

#### 2.1.3. Управление запросами

- [x] Добавление запросов в проект — `tests/test_queries.py::QueryManagementTestCase::test_add_queries_to_project_success`
- [x] Редактирование запросов — `tests/test_queries.py::QueryManagementTestCase`
- [x] Удаление запросов — `tests/test_queries.py::QueryManagementTestCase::test_delete_query_success`
- [x] Импорт запросов из файлов — `tests/test_queries.py::QueryManagementTestCase::test_add_queries_empty_list` (заглушка)
- [x] Группировка запросов — `tests/test_queries.py::ProjectDetailTestCase::test_project_detail_page`
- [x] Поиск и фильтрация запросов — `tests/test_queries.py::QueryManagementTestCase::test_add_queries_project_not_found`

#### 2.1.4. Парсинг позиций

- [x] Создание задачи парсинга — `tests/test_parsing_routes.py::test_run_parser_success`
- [x] Выбор поисковой системы (Google, Яндекс) — `tests/test_parsing_routes.py::test_run_parser_success`, `test_estimate_limits_yandex_search_api`
- [x] Выбор региона — `tests/test_api_routes.py::test_api_locations`, `test_api_yandex_regions`
- [x] Настройка параметров парсинга — `tests/test_parsing_routes.py::test_estimate_limits_google`
- [x] Запуск процесса парсинга — `tests/test_parsing_routes.py::test_run_parser_success`; `tests/test_parsing.py::test_run_parsing_in_thread_success`
- [x] Отслеживание прогресса — `tests/test_parsing_routes.py::test_get_status`
- [x] Просмотр результатов — `tests/test_positions.py::test_show_results`, `test_history_page`
- [x] Экспорт результатов — `tests/test_parsing_routes.py::test_download_session_results_xlsx`, `test_download_session_results_txt`, `test_download_session_results_csv`

#### 2.1.5. Анализ страниц

- [x] Анализ отдельной страницы — `tests/test_page_analyzer_routes.py::test_analyze_pages_success`
- [x] Извлечение метаданных (title, description) — `tests/test_page_analyzer.py::test_extract_page_data_success`
- [x] Извлечение заголовков — `tests/test_page_analyzer.py::test_extract_page_data_success`
- [x] LSI-анализ текста — `tests/test_text_analyzer.py::TestAnalyzeTextContent::test_analyze_russian_text`, `test_ngrams_generation`, `test_word_frequency_calculation`
- [x] Определение объема текста — `tests/test_page_analyzer.py::test_extract_page_data_success`
- [x] Обработка ошибок при анализе — `tests/test_page_analyzer.py::test_extract_page_data_request_error`; `tests/test_page_analyzer_routes.py::test_analyze_pages_create_task_failure`

#### 2.1.6. Кластеризация запросов

- [x] Создание кластеров — `tests/test_clustering.py::ClusteringRoutesTestCase::test_preview_clustering_success`
- [x] Назначение запросов кластерам — `tests/test_clustering.py::HardClusterizerTestCase::test_load_keywords_with_serps`
- [x] Редактирование кластеров — `tests/test_clustering.py::ClusteringIntegrationTestCase::test_preview_clustering_success`
- [x] Просмотр кластеров — `tests/test_clustering.py::ClusteringRoutesTestCase::test_clustering_page_loads`
- [x] Анализ кластеров — `tests/test_clustering.py::HardClusterizerTestCase::test_get_current_groups`

#### 2.1.7. AI-функциональность

- [x] Взаимодействие с AI-сервисом — `tests/test_ai.py::TestDeepSeekService`
- [x] Отправка запросов к AI — `tests/test_ai.py::test_add_message`, `test_send_question`; `tests/test_ai_routes.py::test_ask_ai_success`
- [x] Обработка ответов от AI — `tests/test_ai.py::test_authentication_error`, `test_rate_limit_error`, `test_api_connection_error`
- [x] Валидация API-ключа DeepSeek — `tests/test_ai.py::test_deepseek_service_initialization_invalid_token`, `test_deepseek_service_initialization_empty_token`; `tests/test_ai_routes.py::test_ask_ai_no_api_key`

#### 2.1.8. Управление настройками

- [x] Просмотр глобальных настроек — `tests/test_settings.py::SettingsRoutesTestCase::test_settings_page_loads`
- [x] Изменение настроек — `tests/test_settings.py::SettingsRoutesTestCase::test_update_settings_success`
- [x] Валидация значений настроек — `tests/test_settings.py::SettingsRoutesTestCase::test_update_settings_requires_super_admin`
- [x] Восстановление значений по умолчанию — `tests/test_settings.py::SettingsDatabaseTestCase::test_update_setting`

#### 2.1.9. Отчеты

- [ ] Генерация отчетов
- [x] Экспорт отчетов — `tests/test_parsing_routes.py::test_download_session_results_xlsx`; `tests/test_page_analyzer_routes.py::test_download_analysis_task_txt_format`, `test_download_analysis_task_csv_format`
- [ ] Форматирование отчетов
- [x] Просмотр исторических данных — `tests/test_positions.py::test_history_page`, `tests/test_main_routes.py::test_show_results_without_session`

### 2.2. API тестирование

#### 2.2.1. Аутентификация API

- [x] Тестирование эндпоинтов аутентификации — `tests/test_api_integration.py::test_auth_endpoints_integration`
- [x] Проверка токенов доступа — `tests/test_api_integration.py::test_api_token_validation`
- [x] Проверка сроков действия токенов — `tests/test_api_integration.py::test_api_token_expiration`
- [x] Обработка ошибок аутентификации — `tests/test_api_routes.py::test_api_body_validation`

#### 2.2.2. CRUD операции

- [x] Создание ресурсов через API — `tests/test_api_integration.py::test_project_crud_integration`
- [x] Чтение ресурсов через API — `tests/test_api_integration.py::test_api_projects_endpoint`
- [x] Обновление ресурсов через API — `tests/test_api_integration.py::test_project_crud_integration`
- [x] Удаление ресурсов через API — `tests/test_api_integration.py::test_project_crud_integration`
- [x] Проверка прав доступа к ресурсам — `tests/test_api_integration.py::test_unauthorized_access_to_protected_endpoints`

#### 2.2.3. Операции парсинга

- [x] Запуск задач парсинга через API — `tests/test_parsing_routes.py::test_run_parser_success`
- [x] Получение статуса задач — `tests/test_parsing_routes.py::test_get_status`
- [x] Получение результатов парсинга — `tests/test_positions.py::test_download_session_results`
- [x] Обработка ошибок API — `tests/test_api_routes.py::test_api_check_balance_request_exception`

#### 2.2.4. Валидация данных

- [x] Проверка валидации входных данных — `tests/test_api_routes.py::test_api_estimate_limits_empty_queries`
- [x] Обработка граничных значений — `tests/test_api_routes.py::TestDataValidation::test_api_boundary_values`
- [x] Обработка некорректных данных — `tests/test_api_routes.py::TestDataValidation::test_api_invalid_data_handling`
- [x] Тестирование ограничений — `tests/test_api_routes.py::TestDataValidation::test_api_limit_handling`

### 2.3. Безопасность

#### 2.3.1. Проверка аутентификации

- [x] Доступ к защищенным ресурсам без аутентификации — `tests/test_security.py::test_dashboard_redirect_without_auth`, `test_api_endpoints_require_auth`
- [x] Использование поддельных токенов — `tests/test_security.py::TestTokenSecurity::test_invalid_token_access`
- [x] Проверка сессий — `tests/manual_test_cases.md` §1.2 (сессия осталась валидной — задокументировано)
- [x] Защита от CSRF атак — `tests/test_security.py::TestCSRFProtection`; `tests/test_ui_functional.py::test_login_form_csrf_protection`

#### 2.3.2. Проверка авторизации

- [x] Доступ к ресурсам других пользователей — `tests/test_security.py::test_other_user_data_not_accessible`
- [ ] Попытки обхода ролевой модели
- [x] Проверка прав доступа к API эндпоинтам — `tests/test_security.py::test_api_endpoints_require_auth`

#### 2.3.3. Валидация входных данных

- [x] SQL-инъекции — `tests/test_security.py::TestSQLInjection`
- [x] XSS-атаки — `tests/test_security.py::TestXSSProtection`
- [x] Проверка заголовков — `tests/test_security.py::TestSecurityHeaders`
- [ ] Проверка тела запроса
- [ ] Проверка файловых загрузок

#### 2.3.4. Защита от злоупотреблений

- [x] Ограничение частоты запросов (rate limiting) — `tests/test_security.py::TestRateLimiting`; `tests/test_api_integration.py::test_api_rate_limiting_simulation`
- [ ] Проверка лимитов пользователей
- [ ] Защита от DoS-атак
- [ ] Проверка использования ресурсов

#### 2.3.5. Защита данных

- [ ] Шифрование чувствительных данных
- [x] Проверка хранения паролей — `tests/test_models.py::test_check_password_correct`, `test_check_password_incorrect`; `tests/test_security.py::test_password_not_in_response`
- [ ] Проверка обработки персональных данных
- [ ] Защита от утечек данных

### 2.4. Производительность

#### 2.4.1. Нагрузочное тестирование

- [x] Тестирование под нагрузкой нескольких пользователей — `tests/test_performance.py::TestScalability::test_concurrent_users_simulation`
- [x] Проверка скорости ответа API — `tests/test_performance.py::TestPerformance::test_api_response_time`
- [x] Проверка скорости выполнения парсинга — `tests/test_performance.py::TestPerformance::test_parsing_process_performance`
- [x] Проверка использования памяти — `tests/test_performance.py::TestPerformance::test_memory_usage_simulation`

#### 2.4.2. Тестирование масштабируемости

- [ ] Обработка большого объема данных
- [ ] Проверка работы с большим количеством запросов
- [ ] Проверка работы с большим количеством пользователей

### 2.5. Совместимость

#### 2.5.1. Браузеры

- [x] Chrome — `tests/test_compatibility.py::TestBrowserCompatibility::test_chrome_compatibility_simulation`
- [x] Firefox — `tests/test_compatibility.py::TestBrowserCompatibility::test_firefox_compatibility_simulation`
- [x] Safari — `tests/test_compatibility.py::TestBrowserCompatibility::test_safari_compatibility_simulation`
- [x] Edge — `tests/test_compatibility.py::TestBrowserCompatibility::test_edge_compatibility_simulation`
- [x] Проверка версий браузеров — `tests/test_compatibility.py::TestBrowserCompatibility::test_browser_version_compatibility`

#### 2.5.2. Устройства

- [ ] Десктоп
- [ ] Мобильные устройства
- [ ] Планшеты
- [ ] Адаптивный дизайн

### 2.6. Юзабилити

#### 2.6.1. Интерфейс

- [x] Проверка удобства использования — `tests/test_usability.py::TestUsability::test_intuitive_navigation`
- [x] Проверка навигации — `tests/test_usability.py::TestUsability::test_intuitive_navigation`
- [x] Проверка информационной архитектуры — `tests/test_usability.py::TestUsability::test_clear_information_architecture`
- [x] Проверка доступности — `tests/test_usability.py::TestUserExperience::test_accessibility_features`

#### 2.6.2. Ошибки и уведомления

- [x] Понятные сообщения об ошибках — `tests/test_usability.py::TestErrorHandling::test_clear_error_messages`
- [x] Уведомления о действиях пользователя — `tests/test_usability.py::TestUsability::test_action_notifications`
- [x] Обработка исключительных ситуаций — `tests/test_usability.py::TestErrorHandling::test_user_friendly_error_pages`

## 3. Подходы к тестированию

### 3.1. Автоматизированное тестирование

#### 3.1.1. Модульные тесты

- [x] Тестирование отдельных функций — `tests/test_page_analyzer.py`, `tests/test_parsing.py`, `tests/test_ai.py`
- [x] Тестирование методов классов — `tests/test_models.py::TestUserModel`, `TestProjectModel`, `TestQueryModel`
- [x] Тестирование бизнес-логики — `tests/test_parsing.py::test_run_parsing_in_thread_*`
- [x] Покрытие тестами основных сценариев — реализовано для auth, projects, parsing, page_analyzer, AI, security, API

#### 3.1.2. Интеграционные тесты

- [x] Тестирование взаимодействия между модулями — `tests/test_api_integration.py`
- [ ] Тестирование работы с базой данных (реальная БД, не mock)
- [x] Тестирование API эндпоинтов — `tests/test_api_routes.py`, `tests/test_api_integration.py`
- [ ] Тестирование внешних сервисов (реальные вызовы)

#### 3.1.3. Функциональные тесты

- [x] Тестирование пользовательских сценариев — `tests/test_ui_functional.py`
- [x] Тестирование UI — `tests/test_ui_functional.py::TestAuthPages`, `TestProtectedPages`, `TestNavigationAndLayout`
- [ ] Использование Selenium/WebdriverIO
- [ ] Тестирование различных браузеров

### 3.2. Ручное тестирование

#### 3.2.1. Эксплораторное тестирование

- [ ] Тестирование новых функций
- [ ] Тестирование сложных сценариев
- [ ] Тестирование пользовательского опыта
- [ ] Поиск неожиданного поведения

#### 3.2.2. Тестирование регрессии

- [ ] Проверка уже протестированных функций
- [ ] Проверка после изменений в коде
- [ ] Проверка критических путей

#### 3.2.3. Тестирование безопасности

- [x] Ручная проверка уязвимостей — `tests/manual_test_cases.md` §1.1, §1.2
- [x] Проверка доступа к ресурсам — `tests/manual_test_cases.md` §2.1 (Ок)
- [ ] Тестирование валидации данных (ручное)

## 4. План выполнения тестирования

### 4.1. Этап 1: Подготовка (1-2 дня)

- [x] Подготовка тестовой среды — `tests/` директория создана, pytest настроен
- [x] Подготовка тестовых данных — mock-данные в setUp() каждого тест-кейса
- [x] Установка инструментов для автоматизированного тестирования — pytest, unittest.mock
- [x] Определение приоритетов тестов — реализованы тесты для критических модулей

### 4.2. Этап 2: Модульное тестирование (3-5 дней)

- [x] Написание unit-тестов для основных функций — `test_page_analyzer.py`, `test_parsing.py`, `test_ai.py`
- [x] Написание тестов для моделей данных — `tests/test_models.py`
- [ ] Написание тестов для вспомогательных функций
- [ ] Достижение покрытия 80%+

### 4.3. Этап 3: Интеграционное тестирование (5-7 дней)

- [ ] Тестирование работы с базой данных (реальная БД)
- [x] Тестирование API эндпоинтов — `tests/test_api_integration.py`
- [ ] Тестирование внешних интеграций (реальные вызовы)
- [x] Тестирование сценариев использования — `tests/test_api_integration.py::test_project_crud_integration`

### 4.4. Этап 4: Функциональное тестирование (7-10 дней)

- [x] Тестирование основных пользовательских сценариев — `tests/test_ui_functional.py`
- [x] Тестирование UI/UX — `tests/test_ui_functional.py`
- [x] Тестирование форм и валидации данных — `tests/test_ui_functional.py::TestFormValidation`
- [x] Тестирование отчетов и экспорта — `tests/test_parsing_routes.py`, `tests/test_page_analyzer_routes.py`

### 4.5. Этап 5: Тестирование безопасности (5-7 дней)

- [x] Тестирование аутентификации и авторизации — `tests/test_security.py::TestUnauthorizedAccess`
- [x] Тестирование валидации входных данных — `tests/test_security.py::TestSQLInjection`, `TestXSSProtection`
- [x] Тестирование доступа к ресурсам — `tests/test_security.py`
- [ ] Тестирование API безопасности (токены, заголовки)

### 4.6. Этап 6: API тестирование (3-5 дней)

- [x] Тестирование всех API эндпоинтов — `tests/test_api_routes.py`
- [x] Тестирование аутентификации API — `tests/test_api_integration.py::test_auth_endpoints_integration`
- [x] Тестирование валидации данных — `tests/test_api_routes.py::test_api_estimate_limits_empty_queries`
- [x] Тестирование обработки ошибок — `tests/test_api_routes.py::test_api_check_balance_request_exception`

### 4.7. Этап 7: Ручное тестирование (5-7 дней)

- [x] Эксплораторное тестирование — `tests/manual_test_cases.md` (частично)
- [x] Тестирование пользовательского опыта — `tests/manual_test_cases.md` §2.1 (Ок)
- [ ] Тестирование на разных устройствах
- [ ] Тестирование доступности

### 4.8. Этап 8: Нагрузочное тестирование (2-3 дня)

- [ ] Тестирование под нагрузкой
- [ ] Тестирование производительности
- [ ] Тестирование масштабируемости

### 4.9. Этап 9: Итоговое тестирование и отчет (2-3 дня)

- [ ] Тестирование полного пользовательского пути
- [ ] Подготовка отчетов о тестировании
- [ ] Анализ найденных дефектов
- [ ] Подготовка рекомендаций

## 5. Инструменты для тестирования

### 5.1. Автоматизированное тестирование

- [x] Pytest для unit-тестов — используется во всех тест-файлах (unittest + pytest runner)
- [ ] Requests для API тестирования (отдельный клиент, не Flask test client)
- [ ] Selenium для UI тестирования
- [ ] Coverage.py для измерения покрытия
- [ ] Tox для тестирования в разных окружениях

### 5.2. Ручное тестирование

- [ ] Jira/Bugzilla для отслеживания багов
- [ ] Postman для ручного тестирования API
- [x] Браузеры для UI тестирования — `tests/manual_test_cases.md` §3.1
- [ ] Инструменты разработчика в браузере

### 5.3. Безопасность

- [ ] OWASP ZAP для сканирования уязвимостей
- [ ] Burp Suite для ручного тестирования безопасности
- [ ] Sqlmap для тестирования SQL-инъекций

## 6. Метрики и отчеты

### 6.1. Метрики качества

- [ ] Процент покрытия кода тестами
- [ ] Количество найденных и исправленных багов
- [ ] Время выполнения тестов
- [ ] Процент пройденных тестов

### 6.2. Отчеты

- [ ] Ежедневные отчеты о прогрессе
- [ ] Отчеты о найденных багах
- [ ] Отчет о покрытии тестами
- [ ] Итоговый отчет о тестировании

## 7. Риски и митигации

### 7.1. Риски

- [ ] Недостаточное знание системы для тестирования
- [ ] Изменение требований в процессе тестирования
- [ ] Проблемы с тестовой средой
- [ ] Ограничения по времени

### 7.2. Митигации

- [ ] Проведение обучения по системе
- [ ] Регулярное обновление тестов при изменениях
- [ ] Подготовка резервной тестовой среды
- [ ] Приоритизация тестов по важности
