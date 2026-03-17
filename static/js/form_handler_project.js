// form_handler_project.js - обработчик формы для проекта
// Файл содержит функции для обработки формы добавления варианта парсинга

// Функция для переключения видимости опций Яндекса
function toggleYandexOptions() {
    const engineElement = document.getElementById('engine');
    const yandexOptions = document.getElementById('yandexOptions');
    const yandexTypeElement = document.getElementById('yandex_type');
    const yandexPageLimitOptions = document.getElementById('yandex-page-limit-options');
    const googlePageLimitOptions = document.getElementById('google-page-limit-options');
    const googleLocationWrapper = document.getElementById('google-location-wrapper');
    const yandexLocationWrapper = document.getElementById('yandex-location-wrapper');
    const locationOptions = document.getElementById('location-options');

    if (!engineElement || !yandexTypeElement) {
        console.error('Не найдены необходимые элементы для переключения опций Яндекса');
        return;
    }

    const engine = engineElement.value;
    const yandexType = yandexTypeElement.value;

    if (yandexOptions && locationOptions) {
        if (engine === 'yandex') {
            yandexOptions.classList.remove('hidden');
            locationOptions.classList.remove('hidden');
            if (googleLocationWrapper) googleLocationWrapper.classList.add('hidden');
            if (yandexLocationWrapper) yandexLocationWrapper.classList.remove('hidden');
            if (yandexPageLimitOptions && yandexType === 'live_search') {
                yandexPageLimitOptions.classList.remove('hidden');
            } else if (yandexPageLimitOptions) {
                yandexPageLimitOptions.classList.add('hidden');
            }
        } else if (engine === 'google') {
            yandexOptions.classList.add('hidden');
            if (yandexPageLimitOptions) yandexPageLimitOptions.classList.add('hidden');
            if (googlePageLimitOptions) googlePageLimitOptions.classList.remove('hidden');
            locationOptions.classList.remove('hidden');
            if (googleLocationWrapper) googleLocationWrapper.classList.remove('hidden');
            if (yandexLocationWrapper) yandexLocationWrapper.classList.add('hidden');
        } else {
            yandexOptions.classList.add('hidden');
            if (yandexPageLimitOptions) yandexPageLimitOptions.classList.add('hidden');
            if (googlePageLimitOptions) googlePageLimitOptions.classList.add('hidden');
            locationOptions.classList.add('hidden');
        }
    }
}

// Функция для обработки отправки формы
function handleParserFormSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    // Логируем FormData для отладки
    // console.log('FormData содержимое:', Object.fromEntries(formData.entries()));

    // Определяем параметры в зависимости от выбранной поисковой системы
    const engine = formData.get('engine') || '';
    let searchEngineId, searchTypeId;

    // Преобразуем engine в ID поисковой системы
    if (engine === 'yandex') {
        searchEngineId = 1; // предполагаем, что Yandex = 1
        // Определяем тип поиска в Яндексе
        const yandexType = formData.get('yandex_type') || '';
        if (yandexType === 'search_api') {
            searchTypeId = 2; // Search API
        } else if (yandexType === 'live_search') {
            searchTypeId = 1; // Живой поиск
        } else {
            searchTypeId = 2; // значение по умолчанию
        }
    } else if (engine === 'google') {
        searchEngineId = 2; // предполагаем, что Google = 2
        searchTypeId = 3; // предполагаем, что Google = 3
    } else {
        searchEngineId = 0; // значение по умолчанию
        searchTypeId = 0; // значение по умолчанию
    }

    // Определяем ID устройства
    let deviceId;
    const device = formData.get('device') || '';
    // Теперь мы знаем, что 'device' - это уже ID, поэтому просто преобразуем его в число.
    // Если значение невалидное, установим 1 (десктоп) по умолчанию.
    deviceId = parseInt(device, 10) || 1;

    // console.log('Значение device из formData:', formData.get('device'), 'Определённый deviceId:', deviceId);

    // Определяем ID локации
    let locationId = null;
    if (engine === 'google') {
        // Для кастомного селекта нужно получить значение из скрытого input-поля
        // Ищем скрытое поле рядом с кастомным селектом
        const googleHiddenInput = document.querySelector('#location-select-google + input[type="hidden"]') ||
            document.querySelector('.custom-select-wrapper input[name="loc_id_google"]') ||
            document.querySelector('.custom-select-wrapper input[type="hidden"]');
        if (googleHiddenInput && googleHiddenInput.value) {
            locationId = googleHiddenInput.value;
        } else {
            // Резервный вариант - получаем значение из оригинального select-элемента
            const googleLocationSelect = document.querySelector('#location-select-google');
            if (googleLocationSelect && googleLocationSelect.value) {
                locationId = googleLocationSelect.value;
            }
        }
    } else if (engine === 'yandex') {
        // Для кастомного селекта нужно получить значение из скрытого input-поля
        // Ищем скрытое поле рядом с кастомным селектом
        const yandexHiddenInput = document.querySelector('#location-select-yandex + input[type="hidden"]') ||
            document.querySelector('.custom-select-wrapper input[name="loc_id_yandex"]') ||
            document.querySelector('.custom-select-wrapper input[type="hidden"]');
        if (yandexHiddenInput && yandexHiddenInput.value) {
            locationId = yandexHiddenInput.value;
        } else {
            // Резервный вариант - получаем значение из оригинального select-элемента
            const yandexLocationSelect = document.querySelector('#location-select-yandex');
            if (yandexLocationSelect && yandexLocationSelect.value) {
                locationId = yandexLocationSelect.value;
            }
        }
    }

    // Формируем объект данных для отправки
    const data = {
        project_id: form.dataset.projectId || null, // ID проекта из data-атрибута формы
        name: `Вариант ${engine}`, // Генерируем имя варианта
        search_engine_id: searchEngineId,
        search_type_id: searchTypeId,
        yandex_region_id: engine === 'yandex' ? locationId : null,
        location_id: engine === 'google' ? locationId : null,
        device_id: deviceId, // Отправляем как 'device', чтобы соответствовать бэкенду
        page_limit: engine === 'yandex' ? formData.get('yandex_page_limit') : formData.get('google_page_limit')
    };
    // console.log("Тест", data.page_limit);
    // console.log('device_id в конечном объекте:', data.device_id);

    // Отправляем данные на сервер
    fetch(form.action, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: JSON.stringify(data)
    })
        .then(response => {
            // Проверяем, является ли ответ успешным HTTP-статусом
            if (!response.ok) {
                // Если статус не 2xx, пробуем получить ошибку как JSON
                return response.json().then(errorData => {
                    throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
                }).catch(jsonError => {
                    // Если не удается получить JSON-ошибку, возвращаем текст ошибки
                    if (jsonError instanceof SyntaxError) {
                        // Если ошибка разбора JSON (например, сервер вернул HTML)
                        return response.text().then(text => {
                            console.error('Ошибка сервера (не JSON):', text);
                            throw new Error(`Сервер вернул HTML вместо JSON: ${response.status} ${response.statusText}`);
                        });
                    } else {
                        throw jsonError;
                    }
                });
            }
            // Если ответ успешный, пробуем получить JSON
            return response.json();
        })
        .then(result => {
            if (result.success) {
                // Показываем сообщение об успехе
                Toastify({
                    text: "Вариант успешно добавлен!",
                    duration: 3000,
                    close: true,
                    gravity: "toastify-top",
                    position: "right",
                    style: {
                        background: "#4CAF50"
                    },
                    stopOnFocus: true
                }).showToast();
                // Перезагружаем страницу для обновления списка вариантов
                location.reload();
            } else {
                Toastify({
                    text: "Ошибка при добавлении варианта: " + (result.message || 'Неизвестная ошибка'),
                    duration: 300,
                    close: true,
                    gravity: "toastify-top",
                    position: "right",
                    style: {
                        background: "#EF4444"
                    },
                    stopOnFocus: true
                }).showToast();
            }
        })
        .catch(error => {
            console.error('Ошибка при отправке формы:', error);
            // Проверяем, является ли ошибка синтаксической ошибкой JSON
            if (error.message.includes('JSON') || error.message.includes('HTML')) {
                Toastify({
                    text: "Сервер вернул неожиданный ответ. Пожалуйста, проверьте правильность введенных данных и убедитесь, что все поля заполнены корректно.",
                    duration: 5000,
                    close: true,
                    gravity: "toastify-top",
                    position: "right",
                    style: {
                        background: "#EF4444"
                    },
                    stopOnFocus: true
                }).showToast();
            } else {
                Toastify({
                    text: "Произошла ошибка при добавлении варианта: " + error.message,
                    duration: 3000,
                    close: true,
                    gravity: "toastify-top",
                    position: "right",
                    style: {
                        background: "#EF4444"
                    },
                    stopOnFocus: true
                }).showToast();
            }
        });
}

// Инициализация формы при загрузке DOM
document.addEventListener('DOMContentLoaded', function () {
    const parserForm = document.getElementById('parserForm');
    if (parserForm) {
        parserForm.addEventListener('submit', handleParserFormSubmit);
    }

    // Инициализируем начальное состояние для Yandex опций
    toggleYandexOptions();

    // Инициализация кастомных селектов для локаций
    if (window.CustomSelect) {
        const googleLocationSelect = document.querySelector('#location-select-google');
        if (googleLocationSelect) {
            new CustomSelect('#location-select-google', {
                apiUrl: '/api/locations',
                placeholder: 'Выберите локацию для Google'
            }).setDefault(20949, 'Moscow,Moscow,Russia');
        }

        const yandexLocationSelect = document.querySelector('#location-select-yandex');
        if (yandexLocationSelect) {
            new CustomSelect('#location-select-yandex', {
                apiUrl: '/api/yandex-regions',
                placeholder: 'Выберите регион для Яндекса'
            }).setDefault(213, 'Москва');
        }
    }

    const engineSelect = document.getElementById('engine');
    const yandexTypeSelect = document.getElementById('yandex_type');

    if (engineSelect) {
        engineSelect.addEventListener('change', toggleYandexOptions);
    }

    if (yandexTypeSelect) {
        yandexTypeSelect.addEventListener('change', toggleYandexOptions);
    }
});

