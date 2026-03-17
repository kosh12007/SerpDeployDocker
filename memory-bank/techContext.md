# Tech Context: SERP Анализатор

## Стек технологий

- **Язык**: Python 3.x
- **Backend Framework**: Flask
- **БД**: MySQL (через `mysql-connector-python`)
- **Frontend**: HTML5, Tailwind CSS, Vanilla JavaScript
- **Аутентификация**: Flask-Login
- **Безопасность**: Flask-WTF (CSRF Protection)
- **Кеширование**: Flask-Caching
- **Почта**: Flask-Mail
- **API Парсинга**: XmlRiver (XML/JSON)
- **AI**: OpenAI SDK (DeepSeek API)

## Зависимости (ключевые)

- `pandas`, `openpyxl`: Обработка таблиц и Excel.
- `beautifulsoup4`: Парсинг HTML-страниц в анализаторе.
- `scikit-learn`, `nltk`: Алгоритмы кластеризации.
- `requests`: Внешние API-вызовы.

## Среда разработки

- **Сервер**: WSGI (включая поддержку Passenger для хостинга).
- **Сборка стилей**: Tailwind CSS CLI.
- **Логирование**: Файловые логи в `logs/`.

## Ограничения

- Использование лимитов XmlRiver требует контроля баланса и логирования трат.
- Прямое взаимодействие с БД через SQL-запросы в моделях требует внимательности к безопасности и отсутствию инъекций.
- Все транзакционные запросы (POST/PUT/DELETE) должны быть защищены CSRF-токеном.
