# Документация по системе модальных окон

## 1. Файл: static/js/modal.js

### Класс UniversalModal

Класс `UniversalModal` представляет собой универсальный компонент для работы с модальными окнами в приложении. Он предоставляет основные функции открытия и закрытия модальных окон с возможностью динамического наполнения содержимого.

#### Конструктор

```javascript
constructor(modalId)
```

- **Параметры:**
  - `modalId` (string) - ID элемента модального окна в DOM

- **Функциональность:**
  - Находит элемент модального окна по ID
  - Если элемент не найден, выводит ошибку в консоль
  - Находит элементы закрытия и тела модального окна
  - Добавляет обработчики событий:
    - Клик по кнопке закрытия
    - Клик по фону модального окна (закрытие при клике вне содержимого)
    - Нажатие клавиши Escape

#### Методы

**openModal(content)**

Открывает модальное окно с указанным содержимым.

- **Параметры:**
  - `content` (string | HTMLElement) - Содержимое для вставки в модальное окно

- **Функциональность:**
 - Очищает текущее содержимое тела модального окна
 - Вставляет новое содержимое (строку или DOM-элемент)
  - Компенсирует ширину полосы прокрутки, добавляя padding к body
  - Скрывает прокрутку body
  - Показывает модальное окно (display: flex)

**closeModal()**

Закрывает модальное окно.

- **Функциональность:**
  - Скрывает модальное окно (display: none)
  - Восстанавливает прокрутку body
  - Убирает компенсационный padding у body

### Функция openModalWithContent

```javascript
openModalWithContent(targetId)
```

- **Параметры:**
  - `targetId` (string) - ID элемента, содержимое которого будет клонировано и показано в модальном окне

- **Функциональность:**
  - Находит элемент по ID
  - Клонирует его содержимое
  - Убирает класс 'hidden' у клонированного элемента
  - Открывает модальное окно с клонированным содержимым
  - Проверяет и вызывает специфичные функции инициализации для определенных типов модальных окон:
    - `setupGroupFilterLogic` для 'group-filter-modal-content'
    - `setupDateFilterLogic` для 'date-filter-modal-content'
  - Для других типов вызывает универсальную функцию `populateModalOptions`

### Функция populateFilterOptions

```javascript
populateFilterOptions(filterType, container)
```

### Класс ModalLogicHandler

Класс `ModalLogicHandler` предоставляет гибкий способ регистрации и выполнения специфичной логики для разных типов модальных окон.

#### Конструктор

```javascript
constructor()
```

- **Функциональность:**
  - Инициализирует Map для хранения обработчиков

#### Методы

**registerHandler(targetId, handler)**

Регистрирует обработчик для конкретного типа модального окна.

- **Параметры:**
  - `targetId` (string) - ID целевого элемента
  - `handler` (function) - Функция обработки

- **Функциональность:**
  - Сохраняет обработчик в Map с ключом targetId
  - Выводит сообщение в консоль о регистрации обработчика

**executeHandler(targetId, modalBody)**

Вызывает соответствующий обработчик для указанного типа модального окна.

- **Параметры:**
  - `targetId` (string) - ID целевого элемента
  - `modalBody` (HTMLElement) - Контейнер тела модального окна

- **Функциональность:**
  - Находит зарегистрированный обработчик по targetId
  - Если обработчик найден и это функция, вызывает его с переданным modalBody
  - Если обработчик не найден, вызывает executeGlobalPopulate

**executeGlobalPopulate(targetId, modalBody)**

Вызывает глобальную функцию populateModalOptions, если она доступна.
## 3. Вызовы модальных окон в templates/projects/project_positions.html

### HTML-структура модальных окон

1. **Универсальное модальное окно** (строки 161-182):
   ```html
   <div id="universalModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 h-full w-full z-50 flex items-center justify-center" style="display: none;">
       <div class="relative mx-auto p-5 border w-11/12 md:w-1/2 lg:w-1/3 shadow-lg rounded-md bg-white dark:bg-gray-800">
           <div class="mt-3">
               <div id="modalBody" class="mt-2 px-7 py-3">
                   <h3 class="text-lg font-semibold mb-4" id="confirmation-modal-title"></h3>
                   <p class="mb-2" id="confirmation-modal-queries"></p>
                   <p class="mb-2" id="confirmation-modal-limits"></p>
                   <p class="mb-4" id="confirmation-modal-balance"></p>
               </div>
               <div class="items-center px-4 py-3 flex justify-end space-x-4">
                   <button id="modal-confirm-start-parsing"
                       class="bg-blue-500 dark:bg-dark-button-bg hover:bg-blue-700 dark:hover:bg-dark-button-hover-bg text-white dark:text-dark-button-text font-bold py-2 px-4 rounded">
                       Подтвердить
                   </button>
                   <button id="modal-cancel-start-parsing" class="modal-close bg-gray-500 text-white py-2 px-4 rounded">
                       Отмена
                   </button>
               </div>
           </div>
       </div>
   ```

2. **Контент для фильтра "Группа"** (строки 109-147):
   ```html
   <div id="group-filter-modal-content" class="hidden">
       <div class="filter-options-modal space-y-2">
           <h3 class="text-lg font-semibold mb-4">Фильтр по группам</h3>
           <div>
               <label class="flex items-center">
                   <input type="checkbox" id="group-filter-all" class="form-checkbox h-5 w-5 text-blue-600">
                   <span class="ml-2 text-gray-70 dark:text-gray-300">Все</span>
               </label>
           </div>
           <div>
               <label class="flex items-center">
                   <input type="checkbox" id="group-filter-hide" class="form-checkbox h-5 w-5 text-blue-600">
                   <span class="ml-2 text-gray-70 dark:text-gray-300">Скрыть колонку</span>
               </label>
           </div>
           <hr class="my-2 border-gray-300 dark:border-gray-600">
           {% for group in groups %}
           <div>
               <label class="flex items-center">
                   <input type="checkbox" id="group-{{ group }}" name="group_filter" value="{{ group }}" class="form-checkbox h-5 w-5 text-blue-600 group-filter-item">
                   <span class="ml-2 text-gray-700 dark:text-gray-300">{{ group }}</span>
               </label>
           </div>
           {% endfor %}
           <div>
               <label class="flex items-center">
                   <input type="checkbox" id="group-no-group" name="group_filter" value="Без группы" class="form-checkbox h-5 w-5 text-blue-600 group-filter-item">
                   <span class="ml-2 text-gray-700 dark:text-gray-300">Без группы</span>
               </label>
           </div>
       </div>
       <div class="mt-4 flex justify-end">
           <button id="apply-group-filter" class="bg-blue-500 dark:bg-dark-button-bg hover:bg-blue-700 dark:hover:bg-dark-button-hover-bg text-white dark:text-dark-button-text font-bold py-2 px-4 rounded">
               Применить
           </button>
       </div>
   ```

3. **Контент для фильтра "Дата"** (строки 149-158):
   ```html
   <div id="date-filter-modal-content" class="hidden">
       <h3 class="text-lg font-semibold mb-4">Фильтр по датам</h3>
       <div id="calendar-container" class="calendar-container"></div>
       <div class="mt-4 flex justify-end">
           <button id="apply-date-filter" class="bg-blue-500 dark:bg-dark-button-bg hover:bg-blue-700 dark:hover:bg-dark-button-hover-bg text-white dark:text-dark-button-text font-bold py-2 px-4 rounded">
               Применить
           </button>
       </div>
   ```

### Триггеры модальных окон

1. **Фильтр по группам** (строки 52-56):
   ```html
   <div id="group-filter-select"
       class="modal-trigger p-2 border rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-200 border-gray-300 dark:border-gray-600 cursor-pointer"
       style="max-width: 200px;"
       data-target="group-filter-modal-content"
       data-total-groups="{{ groups|length + 1 }}">
       <span>Фильтр по группам</span>
   </div>
   ```

2. **Фильтр по датам** (строки 59-63):
   ```html
   <div id="date-filter-select"
       class="modal-trigger p-2 border rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-20 border-gray-300 dark:border-gray-600 cursor-pointer"
       style="max-width: 200px;"
       data-target="date-filter-modal-content">
       <span>Фильтр по датам</span>
   </div>
   ```

### JavaScript-логика

1. **Регистрация обработчиков** (строки 723-727):
## 4. Вызовы модальных окон в templates/projects/project_detail.html

### HTML-структура модальных окон

1. **Контент для фильтра "Устройство"** (строки 264-270):
   ```html
   <div id="device-filter-modal-content" class="hidden">
       <h3 class="text-lg font-semibold mb-4">Фильтр по устройству</h3>
       <div class="filter-options-modal">
           <!-- Сюда будет сгенерирован список устройств -->
       </div>
   </div>
   ```

2. **Контент для фильтра "Регион"** (строки 272-278):
   ```html
   <div id="region-filter-modal-content" class="hidden">
       <h3 class="text-lg font-semibold mb-4">Фильтр по региону</h3>
       <div class="filter-options-modal">
           <!-- Сюда будет сгенерирован список регионов -->
       </div>
   </div>
   ```

3. **Контент для фильтра "ПС"** (строки 280-286):
   ```html
   <div id="search-engine-filter-modal-content" class="hidden">
       <h3 class="text-lg font-semibold mb-4">Фильтр по Поисковой Системе</h3>
       <div class="filter-options-modal">
           <!-- Сюда будет сгенерирован список ПС -->
       </div>
   ```

4. **Контент для фильтра "Тип поиска"** (строки 28-294):
   ```html
   <div id="search-type-filter-modal-content" class="hidden">
       <h3 class="text-lg font-semibold mb-4">Фильтр по Типу поиска</h3>
       <div class="filter-options-modal">
           <!-- Сюда будет сгенерирован список типов поиска -->
       </div>
   ```

5. **Универсальное модальное окно** (строки 297-316):
   ```html
   <div id="universalModal"
       class="fixed inset-0 bg-gray-600 bg-opacity-50 h-full w-full z-50 flex items-center justify-center"
       style="display: none !important;">
       <div class="relative mx-auto p-5 border w-11/12 md:w-1/2 lg:w-1/3 shadow-lg rounded-md bg-white dark:bg-gray-800">
           <div class="mt-3">
               <div id="modalBody" class="mt-2 px-7 py-3">
                   <div class="items-center px-4 py-3">
                       <button class="modal-close py-2
                       text-base font-medium rounded-md
                        hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-300">
                           Закрыть
                       </button>
                   </div>
                   <!-- Содержимое будет вставлено сюда -->
               </div>
           </div>
       </div>
   ```

### Триггеры модальных окон

В таблице вариантов парсинга (строки 28-80) каждый заголовок с фильтром имеет класс `modal-trigger`:

1. **Фильтр по типу поиска** (строки 28-38):
   ```html
   <th scope="col"
       class="filter-trigger relative px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-50 uppercase tracking-wider search-type-column cursor-pointer modal-trigger"
       data-target="search-type-filter-modal-content" data-filter-type="search-type">
   ```

2. **Фильтр по поисковой системе** (строки 40-51):
   ```html
   <th scope="col"
       class="filter-trigger relative px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-500 uppercase tracking-wider search-engine-column cursor-pointer modal-trigger"
       data-target="search-engine-filter-modal-content" data-filter-type="search-engine">
   ```

3. **Фильтр по региону** (строки 53-64):
   ```html
   <th scope="col"
       class="filter-trigger relative px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-500 uppercase tracking-wider region-column cursor-pointer modal-trigger"
       data-target="region-filter-modal-content" data-filter-type="region">
   ```

4. **Фильтр по устройству** (строки 66-77):
   ```html
   <th scope="col"
       class="filter-trigger relative px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-500 uppercase tracking-wider device-column cursor-pointer modal-trigger"
       data-target="device-filter-modal-content" data-filter-type="device">
   ```

### JavaScript-логика

1. **Функция populateModalOptions** (строки 703-750):
   - Собирает уникальные значения из таблицы для указанного типа фильтра
   - Создает опции фильтра в модальном окне
   - Назначает обработчики кликов для опций
   - При клике применяет фильтр и закрывает модальное окно

2. **Обработчики фильтров** (строки 599-700):
   - `handleFilterChange` - обрабатывает изменение фильтра
   - `applyAllFilters` - применяет все сохраненные фильтры
   - `updateFilterDisplay` - обновляет отображение фильтра в заголовке таблицы
   ```javascript
   if (window.modalLogicHandler) {
       window.modalLogicHandler.registerHandler('group-filter-modal-content', setupGroupFilterLogic);
       window.modalLogicHandler.registerHandler('date-filter-modal-content', setupDateFilterLogic);
   }
   ```

## 5. Общая архитектура системы модальных окон

### Принципы работы

1. **Универсальность**: Используется один универсальный компонент модального окна для всех типов контента
2. **Динамическое содержимое**: Содержимое модальных окон загружается динамически из скрытых элементов на странице
3. **Специфичная логика**: Для разных типов модальных окон может быть зарегистрирована специфичная логика инициализации
4. **Сохранение состояния**: Некоторые фильтры сохраняют свое состояние в localStorage

### Поток работы с модальным окном

1. Пользователь кликает по элементу с классом `modal-trigger`
2. Система находит ID целевого контента из атрибута `data-target`
3. Клонирует содержимое целевого элемента
4. Открывает универсальное модальное окно с клонированным содержимым
5. Вызывает зарегистрированный обработчик для специфичной логики (если есть)
6. При взаимодействии с модальным окном применяются соответствующие действия
7. Модальное окно закрывается по клику на крестик, вне области окна или по клавише Escape

### Структура данных

- Модальные окна используются для фильтрации данных в таблицах
- Фильтры сохраняют свое состояние в localStorage с ключами, специфичными для проекта
- Каждый фильтр имеет тип (search-type, search-engine, region, device), который используется для определения, какие данные фильтровать
2. **Функция setupGroupFilterLogic** (строки 252-309):
   - Инициализирует логику фильтра по группам
   - Управляет состоянием чекбоксов
   - Обрабатывает применение фильтра
   - Сохраняет состояние в localStorage

3. **Функция setupDateFilterLogic** (строки 731-829):
   - Инициализирует календарь с помощью flatpickr
   - Загружает доступные даты из API
   - Позволяет выбирать диапазоны дат
   - Обрабатывает применение фильтра

- **Параметры:**
  - `targetId` (string) - ID целевого элемента
  - `modalBody` (HTMLElement) - Контейнер тела модального окна

- **Функциональность:**
 - Проверяет наличие глобальной функции populateModalOptions
  - Находит контейнер .filter-options-modal внутри modalBody
  - Вызывает populateModalOptions с targetId и найденным контейнером

### Глобальная переменная window.modalLogicHandler

Создается глобальный экземпляр обработчика:

```javascript
window.modalLogicHandler = new ModalLogicHandler();
```

Это позволяет обращаться к обработчику из любого места в приложении.

### Функция openModalWithContent (переопределение)

Обновленная версия функции открытия модального окна, использующая ModalLogicHandler для вызова специфичной логики.

```javascript
function openModalWithContent(targetId)
```

- **Параметры:**
  - `targetId` (string) - ID элемента, содержимое которого будет клонировано и показано в модальном окне

- **Функциональность:**
  - Находит элемент по ID
  - Клонирует его содержимое
  - Убирает класс 'hidden' у клонированного элемента
  - Открывает модальное окно с клонированным содержимым
  - Через setTimeout вызывает window.modalLogicHandler.executeHandler с targetId и modalBody
- **Параметры:**
  - `filterType` (string) - Тип фильтра (например, 'group', 'date')
  - `container` (HTMLElement) - Контейнер, в который будут добавлены опции фильтра

- **Функциональность:**
  - Собирает уникальные значения для указанного типа фильтра из таблицы #variants-table
  - Создает элементы опций и добавляет их в контейнер
  - Добавляет обработчики кликов для каждой опции
  - При клике на опцию вызывает `handleFilterChange` и закрывает модальное окно

### Инициализация

При загрузке DOM:
- Создается экземпляр `UniversalModal` с ID 'universalModal'
- Назначаются обработчики кликов для элементов с классом 'modal-trigger'
- При клике на триггер вызывается `openModalWithContent` с ID цели из атрибута data-target

## 2. Файл: static/js/modal_logic_handler.js

### Класс ModalLogicHandler

Класс `ModalLogicHandler` предоставляет гибкий способ регистрации и выполнения специфичной логики для разных типов модальных окон.

#### Конструктор

```javascript
constructor()
```

- **Функциональность:**
  - Инициализирует Map для хранения обработчиков

#### Методы

**registerHandler(targetId, handler)**

Регистрирует обработчик для конкретного типа модального окна.

- **Параметры:**
 - `targetId` (string) - ID целевого элемента
  - `handler` (function) - Функция обработки

**executeHandler(targetId, modalBody)**

Вызывает соответствующий обработчик для указанного типа модального окна.

- **Параметры:**
  - `targetId` (string) - ID целевого элемента
  - `modalBody` (HTMLElement) - Контейнер тела модального окна

**executeGlobalPopulate(targetId, modalBody)**

Вызывает глобальную функцию populateModalOptions, если она доступна.

- **Параметры:**
  - `targetId` (string) - ID целевого элемента
  - `modalBody` (HTMLElement) - Контейнер тела модального окна

### Функция openModalWithContent (переопределение)

Обновленная версия функции открытия модального окна, использующая ModalLogicHandler для вызова специфичной логики.

## 3. Вызовы модальных окон в templates/projects/project_positions.html

### HTML-структура модальных окон

1. **Универсальное модальное окно** (строки 161-182):
   ```html
   <div id="universalModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 h-full w-full z-50 flex items-center justify-center" style="display: none;">
       <div class="relative mx-auto p-5 border w-11/12 md:w-1/2 lg:w-1/3 shadow-lg rounded-md bg-white dark:bg-gray-800">
           <div class="mt-3">
               <div id="modalBody" class="mt-2 px-7 py-3">
                   <h3 class="text-lg font-semibold mb-4" id="confirmation-modal-title"></h3>
                   <p class="mb-2" id="confirmation-modal-queries"></p>
                   <p class="mb-2" id="confirmation-modal-limits"></p>
                   <p class="mb-4" id="confirmation-modal-balance"></p>
               </div>
               <div class="items-center px-4 py-3 flex justify-end space-x-4">
                   <button id="modal-confirm-start-parsing" class="bg-blue-500 dark:bg-dark-button-bg hover:bg-blue-700 dark:hover:bg-dark-button-hover-bg text-white dark:text-dark-button-text font-bold py-2 px-4 rounded">
                       Подтвердить
                   </button>
                   <button id="modal-cancel-start-parsing" class="modal-close bg-gray-500 text-white py-2 px-4 rounded">
                       Отмена
                   </button>
               </div>
           </div>
       </div>
   ```

2. **Контент для фильтра "Группа"** (строки 109-147):
   ```html
   <div id="group-filter-modal-content" class="hidden">
       <div class="filter-options-modal space-y-2">
           <h3 class="text-lg font-semibold mb-4">Фильтр по группам</h3>
           <div>
               <label class="flex items-center">
                   <input type="checkbox" id="group-filter-all" class="form-checkbox h-5 w-5 text-blue-600">
                   <span class="ml-2 text-gray-700 dark:text-gray-300">Все</span>
               </label>
           </div>
           <div>
               <label class="flex items-center">
                   <input type="checkbox" id="group-filter-hide" class="form-checkbox h-5 w-5 text-blue-600">
                   <span class="ml-2 text-gray-700 dark:text-gray-300">Скрыть колонку</span>
               </label>
           </div>
           <hr class="my-2 border-gray-300 dark:border-gray-600">
           {% for group in groups %}
           <div>
               <label class="flex items-center">
                   <input type="checkbox" id="group-{{ group }}" name="group_filter" value="{{ group }}" class="form-checkbox h-5 w-5 text-blue-600 group-filter-item">
                   <span class="ml-2 text-gray-700 dark:text-gray-300">{{ group }}</span>
               </label>
           </div>
           {% endfor %}
           <div>
               <label class="flex items-center">
                   <input type="checkbox" id="group-no-group" name="group_filter" value="Без группы" class="form-checkbox h-5 w-5 text-blue-600 group-filter-item">
                   <span class="ml-2 text-gray-70 dark:text-gray-300">Без группы</span>
               </label>
           </div>
       <div class="mt-4 flex justify-end">
           <button id="apply-group-filter" class="bg-blue-500 dark:bg-dark-button-bg hover:bg-blue-700 dark:hover:bg-dark-button-hover-bg text-white dark:text-dark-button-text font-bold py-2 px-4 rounded">
               Применить
           </button>
       </div>
   ```

3. **Контент для фильтра "Дата"** (строки 149-158):
   ```html
   <div id="date-filter-modal-content" class="hidden">
       <h3 class="text-lg font-semibold mb-4">Фильтр по датам</h3>
       <div id="calendar-container" class="calendar-container"></div>
       <div class="mt-4 flex justify-end">
           <button id="apply-date-filter" class="bg-blue-500 dark:bg-dark-button-bg hover:bg-blue-700 dark:hover:bg-dark-button-hover-bg text-white dark:text-dark-button-text font-bold py-2 px-4 rounded">
               Применить
           </button>
       </div>
   </div>
   ```

### Триггеры модальных окон

1. **Фильтр по группам** (строки 52-56):
   ```html
   <div id="group-filter-select"
       class="modal-trigger p-2 border rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-20 border-gray-300 dark:border-gray-600 cursor-pointer"
       style="max-width: 200px;"
       data-target="group-filter-modal-content"
       data-total-groups="{{ groups|length + 1 }}">
       <span>Фильтр по группам</span>
   </div>
   ```

2. **Фильтр по датам** (строки 59-63):
   ```html
   <div id="date-filter-select"
       class="modal-trigger p-2 border rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-20 border-gray-300 dark:border-gray-600 cursor-pointer"
       style="max-width: 200px;"
       data-target="date-filter-modal-content">
       <span>Фильтр по датам</span>
   </div>
   ```

### JavaScript-логика

1. **Регистрация обработчиков** (строки 723-727):
   ```javascript
   if (window.modalLogicHandler) {
       window.modalLogicHandler.registerHandler('group-filter-modal-content', setupGroupFilterLogic);
       window.modalLogicHandler.registerHandler('date-filter-modal-content', setupDateFilterLogic);
   }
   ```

2. **Функция setupGroupFilterLogic** (строки 252-309):
   - Инициализирует логику фильтра по группам
   - Управляет состоянием чекбоксов
   - Обрабатывает применение фильтра
   - Сохраняет состояние в localStorage

3. **Функция setupDateFilterLogic** (строки 731-829):
   - Инициализирует календарь с помощью flatpickr
   - Загружает доступные даты из API
   - Позволяет выбирать диапазоны дат
   - Обрабатывает применение фильтра

## 4. Вызовы модальных окон в templates/projects/project_detail.html

### HTML-структура модальных окон

1. **Контент для фильтра "Устройство"** (строки 264-270):
   ```html
   <div id="device-filter-modal-content" class="hidden">
       <h3 class="text-lg font-semibold mb-4">Фильтр по устройству</h3>
       <div class="filter-options-modal">
           <!-- Сюда будет сгенерирован список устройств -->
       </div>
   </div>
   ```

2. **Контент для фильтра "Регион"** (строки 272-278):
   ```html
   <div id="region-filter-modal-content" class="hidden">
       <h3 class="text-lg font-semibold mb-4">Фильтр по региону</h3>
       <div class="filter-options-modal">
           <!-- Сюда будет сгенерирован список регионов -->
       </div>
   </div>
   ```

3. **Контент для фильтра "ПС"** (строки 280-286):
   ```html
   <div id="search-engine-filter-modal-content" class="hidden">
       <h3 class="text-lg font-semibold mb-4">Фильтр по Поисковой Системе</h3>
       <div class="filter-options-modal">
           <!-- Сюда будет сгенерирован список ПС -->
       </div>
   ```

4. **Контент для фильтра "Тип поиска"** (строки 288-294):
   ```html
   <div id="search-type-filter-modal-content" class="hidden">
       <h3 class="text-lg font-semibold mb-4">Фильтр по Типу поиска</h3>
       <div class="filter-options-modal">
           <!-- Сюда будет сгенерирован список типов поиска -->
       </div>
   ```

5. **Универсальное модальное окно** (строки 297-316):
   ```html
   <div id="universalModal"
       class="fixed inset-0 bg-gray-600 bg-opacity-50 h-full w-full z-50 flex items-center justify-center"
       style="display: none !important;">
       <div class="relative mx-auto p-5 border w-11/12 md:w-1/2 lg:w-1/3 shadow-lg rounded-md bg-white dark:bg-gray-800">
           <div class="mt-3">
               <div id="modalBody" class="mt-2 px-7 py-3">
                   <div class="items-center px-4 py-3">
                       <button class="modal-close py-2
                       text-base font-medium rounded-md
                        hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-300">
                           Закрыть
                       </button>
                   </div>
                   <!-- Содержимое будет вставлено сюда -->
               </div>
           </div>
       </div>
   ```

### Триггеры модальных окон

В таблице вариантов парсинга (строки 28-80) каждый заголовок с фильтром имеет класс `modal-trigger`:

1. **Фильтр по типу поиска** (строки 28-38):
   ```html
   <th scope="col"
       class="filter-trigger relative px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-500 uppercase tracking-wider search-type-column cursor-pointer modal-trigger"
       data-target="search-type-filter-modal-content" data-filter-type="search-type">
   ```

2. **Фильтр по поисковой системе** (строки 40-51):
   ```html
   <th scope="col"
       class="filter-trigger relative px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-50 uppercase tracking-wider search-engine-column cursor-pointer modal-trigger"
       data-target="search-engine-filter-modal-content" data-filter-type="search-engine">
   ```

3. **Фильтр по региону** (строки 53-64):
   ```html
   <th scope="col"
       class="filter-trigger relative px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-500 uppercase tracking-wider region-column cursor-pointer modal-trigger"
       data-target="region-filter-modal-content" data-filter-type="region">
   ```

4. **Фильтр по устройству** (строки 66-77):
   ```html
   <th scope="col"
       class="filter-trigger relative px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-500 uppercase tracking-wider device-column cursor-pointer modal-trigger"
       data-target="device-filter-modal-content" data-filter-type="device">
   ```

### JavaScript-логика

1. **Функция populateModalOptions** (строки 703-750):
   - Собирает уникальные значения из таблицы для указанного типа фильтра
   - Создает опции фильтра в модальном окне
   - Назначает обработчики кликов для опций
   - При клике применяет фильтр и закрывает модальное окно

2. **Обработчики фильтров** (строки 599-700):
   - `handleFilterChange` - обрабатывает изменение фильтра
   - `applyAllFilters` - применяет все сохраненные фильтры
   - `updateFilterDisplay` - обновляет отображение фильтра в заголовке таблицы

## 5. Общая архитектура системы модальных окон

### Принципы работы

1. **Универсальность**: Используется один универсальный компонент модального окна для всех типов контента
2. **Динамическое содержимое**: Содержимое модальных окон загружается динамически из скрытых элементов на странице
3. **Специфичная логика**: Для разных типов модальных окон может быть зарегистрирована специфичная логика инициализации
4. **Сохранение состояния**: Некоторые фильтры сохраняют свое состояние в localStorage

### Поток работы с модальным окном

1. Пользователь кликает по элементу с классом `modal-trigger`
2. Система находит ID целевого контента из атрибута `data-target`
3. Клонирует содержимое целевого элемента
4. Открывает универсальное модальное окно с клонированным содержимым
5. Вызывает зарегистрированный обработчик для специфичной логики (если есть)
6. При взаимодействии с модальным окном применяются соответствующие действия
7. Модальное окно закрывается по клику на крестик, вне области окна или по клавише Escape

### Структура данных

- Модальные окна используются для фильтрации данных в таблицах
- Фильтры сохраняют свое состояние в localStorage с ключами, специфичными для проекта
- Каждый фильтр имеет тип (search-type, search-engine, region, device), который используется для определения, какие данные фильтровать