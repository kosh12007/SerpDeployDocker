class UniversalModal {
    constructor(modalId) {
        this.modal = document.getElementById(modalId);
        if (!this.modal) {
            console.error(`Modal with id ${modalId} not found.`);
            return;
        }
        this.closeButton = this.modal.querySelector('.modal-close');
        this.modalBody = this.modal.querySelector('#modalBody');

        if (this.closeButton) {
            this.closeButton.addEventListener('click', () => this.closeModal());
        }
        this.modal.addEventListener('click', (event) => {
            if (event.target === this.modal) {
                this.closeModal();
            }
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                this.closeModal();
            }
        });
    }

    openModal(contentOrTargetId, callback) {
        if (!this.modalBody) return;
        this.modalBody.innerHTML = '';

        let content;
        if (typeof contentOrTargetId === 'string') {
            const template = document.getElementById(contentOrTargetId);
            if (template) {
                content = template.cloneNode(true);
                content.classList.remove('hidden');
            } else {
                // Если это не ID, считаем, что это просто HTML-строка
                this.modalBody.innerHTML = contentOrTargetId;
                content = this.modalBody;
            }
        } else {
            content = contentOrTargetId;
        }

        if (content.nodeType === Node.ELEMENT_NODE) {
            this.modalBody.appendChild(content);
        }

        // --- Компенсация ширины полосы прокрутки ---
        const scrollBarWidth = window.innerWidth - document.documentElement.clientWidth;
        document.body.style.paddingRight = `${scrollBarWidth}px`;
        document.body.style.overflow = 'hidden';

        this.modal.style.display = 'flex';

        // Вызываем колбэк после того, как модальное окно отобразилось
        if (typeof callback === 'function') {
            // Передаем `modalBody` в колбэк для дальнейших манипуляций
            callback(this.modalBody);
        }
    }

    closeModal() {
        if (!this.modal) return;
        this.modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        document.body.style.paddingRight = ''; // Убираем компенсационный padding
    }
}

function populateFilterOptions(filterType, container) {
    const uniqueValues = new Set();
    // Corrected data attribute selector
    const dataAttribute = `data-${filterType.replace(/-/g, '_')}`;

    document.querySelectorAll(`#variants-table tbody tr`).forEach(row => {
        // Correct attribute name to match the data attributes in the table rows
        const value = row.getAttribute(`data-${filterType.replace('_', '-')}`) || '';
        if (value) uniqueValues.add(value);
    });

    container.innerHTML = '<div class="option-item px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer" data-value="">Все</div>';
    uniqueValues.forEach(value => {
        const option = document.createElement('div');
        option.className = 'option-item px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer';
        option.textContent = value;
        option.setAttribute('data-value', value);
        container.appendChild(option);
    });

    // Re-attach event listeners for the new options
    container.querySelectorAll('.option-item').forEach(option => {
        option.addEventListener('click', function(event) {
            event.stopPropagation();
            const value = this.getAttribute('data-value');
            handleFilterChange(filterType, value);
            if (window.universalModalInstance) {
                window.universalModalInstance.closeModal();
            }
        });
    });
}


document.addEventListener('DOMContentLoaded', function () {
    if (document.getElementById('universalModal')) {
        window.universalModalInstance = new UniversalModal('universalModal');
    }

    document.querySelectorAll('.modal-trigger').forEach(trigger => {
        trigger.addEventListener('click', function () {
            const targetId = this.getAttribute('data-target');
            // Используем новую логику открытия модального окна
            if (window.universalModalInstance && window.modalLogicHandler) {
                const handler = window.modalLogicHandler.getHandler(targetId);
                window.universalModalInstance.openModal(targetId, handler);
            }
        });
    });
});