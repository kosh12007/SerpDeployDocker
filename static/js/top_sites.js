let sessionId = null;

// Эти функции должны быть глобальными, чтобы быть доступными на всех страницах
function showLoading(show) {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) { // Проверяем, существует ли элемент
        if (show) {
            loadingOverlay.classList.remove('hidden');
            loadingOverlay.style.display = 'flex';
        } else {
            loadingOverlay.classList.add('hidden');
            loadingOverlay.style.display = 'none';
        }
    }
}

/**
 * Показывает кастомное модальное окно.
 * @param {string} message - Сообщение для отображения в модальном окне.
 * @param {function|null} confirmCallback - Функция обратного вызова, которая выполняется при подтверждении. Если null, будет показана только кнопка "Закрыть".
 */
function showModal(message, confirmCallback = null) {
    // --- Создание элементов ---
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';

    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content';

    const title = document.createElement('h2');
    title.className = 'modal-title';
    title.textContent = confirmCallback ? 'Подтверждение' : 'Информация';

    const text = document.createElement('p');
    text.className = 'modal-text';
    text.textContent = message;

    const buttons = document.createElement('div');
    buttons.className = 'modal-buttons';

    // --- Функция для закрытия модального окна ---
    const closeModal = () => {
        if (document.body.contains(overlay)) {
            document.body.removeChild(overlay);
        }
    };

    // --- Кнопка "Отмена" или "Закрыть" ---
    const cancelButton = document.createElement('button');
    cancelButton.className = 'modal-button modal-button-cancel';
    cancelButton.textContent = confirmCallback ? 'Отмена' : 'Закрыть';
    cancelButton.addEventListener('click', closeModal);

    // --- Кнопка "Подтвердить" (если есть callback) ---
    if (confirmCallback) {
        const confirmButton = document.createElement('button');
        confirmButton.className = 'modal-button modal-button-confirm';
        confirmButton.textContent = 'Подтвердить';
        confirmButton.addEventListener('click', () => {
            closeModal();
            confirmCallback();
        });
        buttons.appendChild(confirmButton);
    }

    buttons.appendChild(cancelButton);

    // --- Сборка модального окна ---
    modalContent.appendChild(title);
    modalContent.appendChild(text);
    modalContent.appendChild(buttons);
    overlay.appendChild(modalContent);

    // --- Закрытие по клику на оверлей ---
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeModal();
        }
    });

    // --- Добавление на страницу ---
    document.body.appendChild(overlay);
}


document.addEventListener('DOMContentLoaded', function () {
    // Весь код, связанный с формой, будет выполняться только если форма есть на странице
    const parserForm = document.getElementById('parserForm');
    if (parserForm) {
        parserForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = getFormData();
            showLoading(true);

            fetch('/estimate-limits', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: formData
            })
                .then(response => response.json())
                .then(data => {
                    showLoading(false);
                    if (data.error) {
                        showModal(data.error);
                    } else {
                        handleLimitEstimation(data, formData);
                    }
                })
                .catch(error => {
                    showLoading(false);
                    console.error('Ошибка при оценке лимитов:', error);
                    showModal('Не удалось связаться с сервером для оценки лимитов.');
                });
        });

        function handleLimitEstimation(data, formData) {
            const { estimated_limits, available_limits } = data;

            if (estimated_limits > available_limits) {
                const errorMessage = `Для выполнения задачи требуется примерно ${estimated_limits} лимитов, но у вас в наличии только ${available_limits}. Пожалуйста, пополните баланс.`;
                showModal(errorMessage);
            } else {
                const confirmationMessage = `Для выполнения задачи потребуется примерно ${estimated_limits} лимитов. Продолжить?`;
                showModal(confirmationMessage, () => {
                    startParsing(formData);
                });
            }
        }

        function startParsing(formData) {
            showLoading(true);
            fetch('/start-top-sites-parsing', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: formData
            })
                .then(response => response.json())
                .then(data => {
                    showLoading(false);
                    if (data.status === 'success') {
                        const redirectUrl = document.getElementById('parserForm').dataset.redirectUrl;
                        window.location.href = redirectUrl;
                    } else {
                        showModal(data.message || 'Ошибка при запуске парсинга');
                    }
                })
                .catch(error => {
                    showLoading(false);
                    console.error('Ошибка при запуске парсинга:', error);
                    showModal('Не удалось запустить задачу. Пожалуйста, попробуйте еще раз.');
                });
        }

        function getFormData() {
            const formData = new FormData();
            const engine = document.getElementById('engine').value;
            const queries = document.getElementById('queries').value;
            const queryLines = queries.split('\n').filter(line => line.trim() !== '');

            queryLines.forEach(query => {
                formData.append('queries', query);
            });

            formData.append('search_engine', engine);
            formData.append('yandex_type', document.getElementById('yandex_type').value);
            formData.append('yandex_page_limit', document.getElementById('yandex_page_limit').value);
            formData.append('google_page_limit', document.getElementById('google_page_limit').value);

            let loc_id;
            if (engine === 'google') {
                const googleInput = document.querySelector('#google-location-wrapper input[name="loc_id_google"]');
                if (googleInput) loc_id = googleInput.value;
            } else {
                const yandexInput = document.querySelector('#yandex-location-wrapper input[name="loc_id_yandex"]');
                if (yandexInput) loc_id = yandexInput.value;
            }
            if (loc_id) {
                formData.append('loc_id', loc_id);
            }

            formData.append('region', 'RU');
            formData.append('device', 'desktop');

            return formData;
        }

        toggleYandexOptions();

        if (document.querySelector('#location-select-google')) {
            new CustomSelect('#location-select-google', {
                apiUrl: '/api/locations',
                placeholder: 'Выберите локацию для Google'
            }).setDefault(20949, 'Moscow,Moscow,Russia');
        }

        if (document.querySelector('#location-select-yandex')) {
            new CustomSelect('#location-select-yandex', {
                apiUrl: '/api/yandex-regions',
                placeholder: 'Выберите регион для Яндекса'
            }).setDefault(213, 'Москва');
        }

        const queriesTextarea = document.getElementById('queries');
        const queriesCountDiv = document.getElementById('queriesCount');
        const maxQueriesWarningDiv = document.getElementById('maxQueriesWarning');
        const configElement = document.getElementById('config');

        if (configElement) {
            const maxQueries = parseInt(configElement.dataset.maxQueries) || 5;

            if (maxQueriesWarningDiv) {
                maxQueriesWarningDiv.innerText = `Максимум ${maxQueries} фраз. Лишние фразы будут проигнорированы.`;
            }

            if (queriesTextarea) {
                queriesTextarea.addEventListener('input', function () {
                    const lines = this.value.split('\n');
                    const nonEmptyLines = lines.filter(line => line.trim() !== '');
                    const count = nonEmptyLines.length;

                    if (count > maxQueries) {
                        const trimmedLines = nonEmptyLines.slice(0, maxQueries);
                        this.value = trimmedLines.join('\n');
                        if (queriesCountDiv) {
                            queriesCountDiv.innerHTML = `<span style="color: red;">Фраз: ${maxQueries} (достигнут лимит)</span>`;
                        }
                    } else if (queriesCountDiv) {
                        queriesCountDiv.innerText = `Фраз: ${count}`;
                    }
                });
            }
        }

        const engineElement = document.getElementById('engine');
        if (engineElement) {
            engineElement.addEventListener('change', toggleYandexOptions);
        }

        const yandexTypeElement = document.getElementById('yandex_type');
        if (yandexTypeElement) {
            yandexTypeElement.addEventListener('change', toggleYandexOptions);
        }
    }

    // --- Логика для аккордеона, должна работать на всех страницах ---
    const toggleButtons = document.querySelectorAll('.toggle-btn');
    if (toggleButtons.length > 0) {
        toggleButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                event.stopPropagation();
                const accordion = button.closest('.task-accordion');
                if (accordion) {
                    const content = accordion.querySelector('.task-content');
                    if (content) {
                        content.classList.toggle('hidden');
                        button.textContent = content.classList.contains('hidden') ? 'Раскрыть' : 'Свернуть';
                    }
                }
            });
        });
    }
});

function toggleYandexOptions() {
    const engineElement = document.getElementById('engine');
    const yandexOptions = document.getElementById('yandexOptions');
    const yandexTypeElement = document.getElementById('yandex_type');
    const yandexPageLimitOptions = document.getElementById('yandex-page-limit-options');
    const googlePageLimitOptions = document.getElementById('google-page-limit-options');
    const googleLocationWrapper = document.getElementById('google-location-wrapper');
    const yandexLocationWrapper = document.getElementById('yandex-location-wrapper');
    const locationOptions = document.getElementById('location-options');

    // Если одного из ключевых элементов нет, прекращаем выполнение
    if (!engineElement || !yandexOptions || !yandexTypeElement || !yandexPageLimitOptions || !googlePageLimitOptions || !googleLocationWrapper || !yandexLocationWrapper || !locationOptions) {
        return;
    }

    const engine = engineElement.value;
    const yandexType = yandexTypeElement.value;

    if (engine === 'yandex') {
        yandexOptions.classList.remove('hidden');
        googlePageLimitOptions.classList.add('hidden');
        googleLocationWrapper.classList.add('hidden');
        yandexLocationWrapper.classList.remove('hidden');
        locationOptions.classList.remove('hidden');
        if (yandexType === 'live_search') {
            yandexPageLimitOptions.classList.remove('hidden');
        } else {
            yandexPageLimitOptions.classList.add('hidden');
        }
    } else if (engine === 'google') {
        yandexOptions.classList.add('hidden');
        yandexPageLimitOptions.classList.add('hidden');
        googlePageLimitOptions.classList.remove('hidden');
        locationOptions.classList.remove('hidden');
        googleLocationWrapper.classList.remove('hidden');
        yandexLocationWrapper.classList.add('hidden');
    } else {
        yandexOptions.classList.add('hidden');
        yandexPageLimitOptions.classList.add('hidden');
        googlePageLimitOptions.classList.add('hidden');
        locationOptions.classList.add('hidden');
        googleLocationWrapper.classList.add('hidden');
        yandexLocationWrapper.classList.add('hidden');
    }
}

// --- Action Functions ---
function downloadTopSitesTask(taskId, format) {
    window.open(`/download-top-sites/${taskId}?format=${format}`, '_blank');
}

function deleteTopSitesTask(taskId, event) {
    console.log('deleteTopSitesTask вызвана с sessionId:', taskId);
    const confirmButton = document.createElement('button');
    confirmButton.className = 'bg-green-500 hover:bg-green-700 text-white font-bold py-1 px-2 rounded ml-2 toast-confirm-btn';
    confirmButton.textContent = 'Да';

    const cancelButton = document.createElement('button');
    cancelButton.className = 'bg-gray-500 hover:bg-gray-700 text-white font-bold py-1 px-2 rounded ml-1 toast-cancel-btn';
    cancelButton.textContent = 'Отмена';

    const notification = Toastify({
        node: (() => {
            const div = document.createElement('div');
            div.innerHTML = "Вы уверены, что хотите удалить эту сессию? Это действие необратимо. ";
            div.appendChild(confirmButton);
            div.appendChild(cancelButton);
            return div;
        })(),
        duration: -1,
        close: false,
        gravity: "top",
        position: "center",
        style: {
            background: "#EF4444"
        },
        stopOnFocus: false,
        escapeMarkup: false,
        offset: { x: 0, y: 0 }
    }).showToast();

    setTimeout(() => {
        try {
            const toastElement = document.querySelector('.toastify');
            if (toastElement) {
                const confirmBtn = toastElement.querySelector('.toast-confirm-btn');
                const cancelBtn = toastElement.querySelector('.toast-cancel-btn');

                if (confirmBtn) {
                    confirmBtn.onclick = function (e) {
                        e.stopPropagation();
                        fetch(`/delete-top-sites/${taskId}`, {
                            method: 'DELETE',
                            headers: {
                                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                            },
                        })
                            .then(response => response.json().then(data => ({ ok: response.ok, data })))
                            .then(({ ok, data }) => {
                                if (ok) {
                                    const sessionElement = document.getElementById('task-' + taskId);
                                    if (sessionElement) {
                                        sessionElement.remove();
                                    }
                                    Toastify({
                                        text: data.message || "Задача успешно удалена",
                                        duration: 1000,
                                        style: {
                                            background: "#4CAF50"
                                        },
                                    }).showToast();
                                } else {
                                    Toastify({
                                        text: data.message || "Не удалось удалить задачу",
                                        duration: 1000,
                                        style: {
                                            background: "#EF4444"
                                        },

                                    }).showToast();
                                }
                            })
                            .catch(error => {
                                Toastify({
                                    text: "Произошла ошибка при отправке запроса.",
                                    duration: 1000,
                                    style: {
                                        background: "#EF4444"
                                    },
                                }).showToast();
                                console.error('Ошибка fetch:', error);
                            });
                        notification.hideToast();
                    };
                }
                if (cancelBtn) {
                    cancelBtn.onclick = function (e) {
                        e.stopPropagation();
                        notification.hideToast();
                    };
                }
            }
        } catch (error) {
            console.error('Ошибка в обработчике кнопок подтверждения:', error);
        }
    }, 100);
}
function pollStatus(currentSessionId) {
    sessionId = currentSessionId;
    fetch(`/status/${sessionId}`)
        .then(response => response.json())
        .then(data => {
            const progressBar = document.getElementById('progressFill');
            const statusText = document.getElementById('statusText');
            const viewResultsBtn = document.getElementById('viewResultsBtn');

            if (progressBar && statusText) {
                progressBar.style.width = data.progress + '%';
                statusText.innerText = data.status;

                if (data.progress === 100) {
                    statusText.innerText = 'Парсинг завершен!';
                    if (viewResultsBtn) {
                        viewResultsBtn.classList.remove('hidden');
                        viewResultsBtn.onclick = function () {
                            window.location.href = `/results/${sessionId}`;
                        };
                    }
                } else if (data.status.startsWith('Ошибка')) {
                    // Остановка опроса при ошибке
                } else {
                    setTimeout(() => pollStatus(currentSessionId), 2000);
                }
            }
        })
        .catch(error => {
            console.error('Ошибка при опросе статуса:', error);
            if (document.getElementById('statusText')) {
                document.getElementById('statusText').innerText = 'Ошибка при обновлении статуса.';
            }
        });
}