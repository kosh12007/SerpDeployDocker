# Спецификация модуля Hard-кластеризации запросов

## Общее описание
Необходимо добавить функционал Hard-кластеризации ключевых слов в существующий Flask-проект. 
Кластеризация базируется на сравнении ТОП-10 выдачи (SERP), которые уже хранятся в БД.
Метод: Hard (все запросы в группе должны иметь N общих URL с маркером/центром группы).

## Технологический стек
- Backend: Python (Flask)
- Database: MySQL
- Frontend: JS (Vanilla/Fetch), Tailwind CSS, HTML
- Библиотеки: `json`, `urllib.parse`

## Структура Базы Данных (Существующая)
1. `keywords`: (id, project_id, name, volume, group_id)
2. `groups`: (id, project_id, name, total_volume)
3. `parsing_position_results`: (id, query_id, top_10_urls, created_at)
   - `top_10_urls` хранится в формате JSON: `["https://url1.com", "https://url2.com", ...]`

## Логика алгоритма (Backend)

### 1. Подготовка (Service Layer)
- Класс `HardClusterizer` принимает `project_id` и `threshold` (минимум совпадений URL).
- Метод `normalize_url(url)`: 
    - Приводит к нижнему регистру.
    - Убирает `http://`, `https://`, `www.`.
    - Убирает завершающий слеш `/`.
    - Пример: `https://www.site.ru/page/` -&gt; `site.ru/page`.

### 2. Процесс кластеризации (In-memory)
- Загрузить последние записи из `parsing_position_results` для каждого `query_id` проекта.
- Отсортировать ключевые слова по `volume` (DESC). Самый частотный становится "Маркером".
- Для каждого Маркера найти нераспределенные запросы, у которых пересечение множеств URL &gt;= `threshold`.

### 3. Режим "Было/Стало"
- Система не должна вносить изменения в БД сразу.
- Эндпоинт должен возвращать JSON объект:
    - `was`: текущие группы и их состав.
    - `became`: рассчитанные группы и их состав.

## API Endpoints

### 1. `POST /clustering/preview`
- **Input**: `{ project_id: int, threshold: int }`
- **Output**: JSON с данными для сравнения.

### 2. `POST /clustering/apply`
- **Logic**: 
    1. Удалить старые записи в `groups` для этого `project_id`.
    2. Сбросить `group_id` в `keywords`.
    3. Создать новые `groups` и обновить `keywords.group_id`.

## Frontend (Интерфейс)
- Двухколоночный макет (Grid 2 cols).
- Левая колонка: "Текущая структура" (Was).
- Правая колонка: "Новая структура" (Became).
- Интерактив: Слайдер для настройки `threshold` (от 2 до 10) и кнопка "Предпросмотр".
- Кнопка "Применить изменения", которая вызывает финальную запись в БД.

## Пример кода для Backend (Python)
```python
import json
from urllib.parse import urlparse

def normalize_url(url):
    p = urlparse(url)
    domain = p.netloc.replace('www.', '').lower()
    path = p.path.rstrip('/')
    return f"{domain}{path}"

def run_hard_clustering(keywords_with_urls, threshold=3):
    # keywords_with_urls: list of dicts {'id', 'name', 'vol', 'urls_set'}
    sorted_kws = sorted(keywords_with_urls, key=lambda x: x['vol'], reverse=True)
    clusters = []
    used_ids = set()

    for item in sorted_kws:
        if item['id'] in used_ids: continue
        
        current_cluster = {'main': item, 'members': [item]}
        used_ids.add(item['id'])

        for candidate in sorted_kws:
            if candidate['id'] in used_ids: continue
            if len(item['urls_set'].intersection(candidate['urls_set'])) &gt;= threshold:
                current_cluster['members'].append(candidate)
                used_ids.add(candidate['id'])
        clusters.append(current_cluster)
    return clusters


---

### Как использовать этот файл:
1. Создайте в корне проекта файл `clustering_spec.md`.
2. Вставьте туда текст выше.
3. В IDE (например, Cursor) напишите промпт:
   &gt; *"Прочитай файл clustering_spec.md. На основе описанной структуры БД и алгоритма создай: 1) Новый сервисный слой в `services/clustering_service.py`, 2) Маршруты в Flask `routes/clustering.py`, 3) Фронтенд на Tailwind для сравнения "Было/Стало". Используй существующее подключение к MySQL."*

### Дополнительные рекомендации для AI:
* **Пагинация/Лимиты:** Если в проекте &gt; 5000 запросов, попроси AI добавить индикатор загрузки (Spinner), так как сравнение множеств может занять пару секунд.
* **Обработка пустых данных:** Укажи AI, чтобы он игнорировал запросы, по которым в `parsing_position_results` еще нет данных ТОП-10 (или выводил их в группу "Не кластеризовано").

Для того чтобы AI в вашей IDE (Cursor, Windsurf, Copilot) смог корректно реализовать функционал, я подготовил структурированный технический проект в формате Markdown. Вы можете создать файл clustering_spec.md и скормить его AI.
Файл: clustering_spec.md
# Спецификация модуля Hard-кластеризации запросов

## Общее описание
Необходимо добавить функционал Hard-кластеризации ключевых слов в существующий Flask-проект. 
Кластеризация базируется на сравнении ТОП-10 выдачи (SERP), которые уже хранятся в БД.
Метод: Hard (все запросы в группе должны иметь N общих URL с маркером/центром группы).

## Технологический стек
- Backend: Python (Flask)
- Database: MySQL
- Frontend: JS (Vanilla/Fetch), Tailwind CSS, HTML
- Библиотеки: `json`, `urllib.parse`

## Структура Базы Данных (Существующая)
1. `keywords`: (id, project_id, name, volume, group_id)
2. `groups`: (id, project_id, name, total_volume)
3. `parsing_position_results`: (id, query_id, top_10_urls, created_at)
   - `top_10_urls` хранится в формате JSON: `["https://url1.com", "https://url2.com", ...]`

## Логика алгоритма (Backend)

### 1. Подготовка (Service Layer)
- Класс `HardClusterizer` принимает `project_id` и `threshold` (минимум совпадений URL).
- Метод `normalize_url(url)`: 
    - Приводит к нижнему регистру.
    - Убирает `http://`, `https://`, `www.`.
    - Убирает завершающий слеш `/`.
    - Пример: `https://www.site.ru/page/` -> `site.ru/page`.

### 2. Процесс кластеризации (In-memory)
- Загрузить последние записи из `parsing_position_results` для каждого `query_id` проекта.
- Отсортировать ключевые слова по `volume` (DESC). Самый частотный становится "Маркером".
- Для каждого Маркера найти нераспределенные запросы, у которых пересечение множеств URL >= `threshold`.

### 3. Режим "Было/Стало"
- Система не должна вносить изменения в БД сразу.
- Эндпоинт должен возвращать JSON объект:
    - `was`: текущие группы и их состав.
    - `became`: рассчитанные группы и их состав.

## API Endpoints

### 1. `POST /clustering/preview`
- **Input**: `{ project_id: int, threshold: int }`
- **Output**: JSON с данными для сравнения.

### 2. `POST /clustering/apply`
- **Logic**: 
    1. Удалить старые записи в `groups` для этого `project_id`.
    2. Сбросить `group_id` в `keywords`.
    3. Создать новые `groups` и обновить `keywords.group_id`.

## Frontend (Интерфейс)
- Двухколоночный макет (Grid 2 cols).
- Левая колонка: "Текущая структура" (Was).
- Правая колонка: "Новая структура" (Became).
- Интерактив: Слайдер для настройки `threshold` (от 2 до 10) и кнопка "Предпросмотр".
- Кнопка "Применить изменения", которая вызывает финальную запись в БД.

## Пример кода для Backend (Python)
```python
import json
from urllib.parse import urlparse

def normalize_url(url):
    p = urlparse(url)
    domain = p.netloc.replace('www.', '').lower()
    path = p.path.rstrip('/')
    return f"{domain}{path}"

def run_hard_clustering(keywords_with_urls, threshold=3):
    # keywords_with_urls: list of dicts {'id', 'name', 'vol', 'urls_set'}
    sorted_kws = sorted(keywords_with_urls, key=lambda x: x['vol'], reverse=True)
    clusters = []
    used_ids = set()

    for item in sorted_kws:
        if item['id'] in used_ids: continue
        
        current_cluster = {'main': item, 'members': [item]}
        used_ids.add(item['id'])

        for candidate in sorted_kws:
            if candidate['id'] in used_ids: continue
            if len(item['urls_set'].intersection(candidate['urls_set'])) >= threshold:
                current_cluster['members'].append(candidate)
                used_ids.add(candidate['id'])
        clusters.append(current_cluster)
    return clusters


---

### Как использовать этот файл:
1. Создайте в корне проекта файл `clustering_spec.md`.
2. Вставьте туда текст выше.
3. В IDE (например, Cursor) напишите промпт:
   > *"Прочитай файл clustering_spec.md. На основе описанной структуры БД и алгоритма создай: 1) Новый сервисный слой в `services/clustering_service.py`, 2) Маршруты в Flask `routes/clustering.py`, 3) Фронтенд на Tailwind для сравнения "Было/Стало". Используй существующее подключение к MySQL."*

### Дополнительные рекомендации для AI:
* **Пагинация/Лимиты:** Если в проекте > 5000 запросов, попроси AI добавить индикатор загрузки (Spinner), так как сравнение множеств может занять пару секунд.
* **Обработка пустых данных:** Укажи AI, чтобы он игнорировал запросы, по которым в `parsing_position_results` еще нет данных ТОП-10 (или выводил их в группу "Не кластеризовано").

<div id="preview-modal" class="hidden fixed inset-0 bg-gray-900 bg-opacity-50 overflow-y-auto h-full w-full"> <div class="relative top-10 mx-auto p-5 border w-11/12 shadow-lg rounded-md bg-white"> <div class="flex justify-between items-center border-b pb-3 mb-4"> <h3 class="text-2xl font-bold text-gray-800">Сравнение кластеризации</h3> <button onclick="closeModal()" class="text-gray-400 hover:text-gray-600">&times;</button> </div> <div class="grid grid-cols-2 gap-8"> <div class="bg-gray-50 p-4 rounded-lg border border-dashed border-gray-300"> <h4 class="text-lg font-semibold text-gray-500 mb-4 uppercase tracking-wider">Было (Текущие группы)</h4> <div id="was-container" class="space-y-4"> </div> </div> <div class="bg-blue-50 p-4 rounded-lg border border-blue-200"> <h4 class="text-lg font-semibold text-blue-600 mb-4 uppercase tracking-wider">Стало (Новая Hard-группировка)</h4> <div id="became-container" class="space-y-4"> </div> </div> </div> <div class="mt-8 flex justify-end space-x-4 border-t pt-4"> <button onclick="closeModal()" class="px-6 py-2 bg-gray-200 text-gray-700 rounded-md">Оставить как есть</button> <button onclick="applyClustering()" class="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 shadow-lg"> Применить новый вариант </button> </div> </div> </div>

KO
Вы
21:50
@app.route('/api/clustering/preview', methods=['POST']) def preview_clustering(): data = request.json project_id = data.get('project_id') threshold = int(data.get('threshold', 3)) conn = get_db_connection() clusterizer = HardClusterizer(conn, project_id, threshold) # 1. Загружаем данные для расчета clusterizer.load_data() # 2. Получаем новый вариант (СТАЛО) new_clusters_raw = clusterizer.run() # Форматируем для фронтенда became_data = [] for c in new_clusters_raw: became_data.append({ "name": c['main_keyword']['text'], "total_vol": sum(m['volume'] for m in c['members']), "keywords": [m['text'] for m in c['members']] }) # 3. Получаем текущее состояние (БЫЛО) cursor = conn.cursor(dictionary=True) cursor.execute(""" SELECT g.name as group_name, k.name as kw_name, k.volume FROM groups g JOIN keywords k ON g.id = k.group_id WHERE g.project_id = %s """, (project_id,)) was_rows = cursor.fetchall() # Группируем для удобства отображения was_data_map = {} for row in was_rows: if row['group_name'] not in was_data_map: was_data_map[row['group_name']] = {"name": row['group_name'], "keywords": [], "total_vol": 0} was_data_map[row['group_name']]["keywords"].append(row['kw_name']) was_data_map[row['group_name']]["total_vol"] += (row['volume'] or 0) return jsonify({ "was": list(was_data_map.values()), "became": became_data })