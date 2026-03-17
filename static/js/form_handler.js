document.addEventListener('DOMContentLoaded', function () {
    const parserForm = document.getElementById('parserForm');
    if (!parserForm) return;

    const estimateUrl = parserForm.dataset.estimateUrl;
    const startUrl = parserForm.dataset.startUrl;
    const redirectUrl = parserForm.dataset.redirectUrl;

    parserForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const formData = getFormData(parserForm.id);
        if (!formData) return;

        showLoading(true);

        fetch(estimateUrl, {
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
                handleLimitEstimation(data, formData, startUrl, redirectUrl);
            }
        })
        .catch(error => {
            showLoading(false);
            console.error('Ошибка при оценке лимитов:', error);
            showModal('Не удалось связаться с сервером для оценки лимитов.');
        });
    });
});

function handleLimitEstimation(data, formData, startUrl, redirectUrl) {
    const { estimated_limits, available_limits } = data;

    if (estimated_limits > available_limits) {
        const errorMessage = `Для выполнения задачи требуется примерно ${estimated_limits} лимитов, но у вас в наличии только ${available_limits}. Пожалуйста, пополните баланс.`;
        showModal(errorMessage);
    } else {
        const confirmationMessage = `Для выполнения задачи потребуется примерно ${estimated_limits} лимитов. Продолжить?`;
        showModal(confirmationMessage, () => {
            startParsing(formData, startUrl, redirectUrl);
        });
    }
}

function startParsing(formData, startUrl, redirectUrl) {
    showLoading(true);
    fetch(startUrl, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        showLoading(false);
        if (data.status === 'success' || data.status === 'started') {
            let finalRedirectUrl = redirectUrl;
            if (data.session_id) {
                finalRedirectUrl += `?session_id=${data.session_id}`;
            }
            window.location.href = finalRedirectUrl;
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

function getFormData(formId) {
    if (formId === 'parserForm') { // ID для index.html
        return getIndexFormData();
    } else if (formId === 'topSitesParserForm') { // Новый ID для top_sites.html
        return getTopSitesFormData();
    }
    return null;
}

function getIndexFormData() {
    const form = document.getElementById('parserForm');
    const formData = new FormData(form);
    // Дополнительная логика для формы index, если нужна
    return formData;
}

function getTopSitesFormData() {
    const form = document.getElementById('topSitesParserForm');
    const formData = new FormData();
    const engine = form.querySelector('#engine').value;
    const queries = form.querySelector('#queries').value;
    const queryLines = queries.split('\n').filter(line => line.trim() !== '');

    queryLines.forEach(query => {
        formData.append('queries', query);
    });

    formData.append('search_engine', engine);
    formData.append('yandex_type', form.querySelector('#yandex_type').value);
    formData.append('yandex_page_limit', form.querySelector('#yandex_page_limit').value);
    formData.append('google_page_limit', form.querySelector('#google_page_limit').value);

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


// Глобальные функции для модального окна и загрузчика
function showLoading(show) {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = show ? 'flex' : 'none';
    }
}

function showModal(message, confirmCallback = null) {
    const existingModal = document.querySelector('.modal-overlay');
    if (existingModal) {
        existingModal.remove();
    }

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

    const closeModal = () => {
        if (document.body.contains(overlay)) {
            document.body.removeChild(overlay);
        }
    };

    const cancelButton = document.createElement('button');
    cancelButton.className = 'modal-button modal-button-cancel';
    cancelButton.textContent = confirmCallback ? 'Отмена' : 'Закрыть';
    cancelButton.addEventListener('click', closeModal);

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
    modalContent.appendChild(title);
    modalContent.appendChild(text);
    modalContent.appendChild(buttons);
    overlay.appendChild(modalContent);

    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeModal();
        }
    });

    document.body.appendChild(overlay);
}