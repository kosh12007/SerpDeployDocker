/**
 * Модуль селектора проектов для главного меню
 * Позволяет выбирать проект из списка с поиском в реальном времени
 * Поддерживает десктопную и мобильную версию
 */

class ProjectSelector {
    constructor() {
        // Кэш загруженных проектов
        this.projects = [];
        // Флаг загрузки
        this.isLoading = false;
        // Флаг открытия модального окна
        this.isOpen = false;

        // Инициализация после загрузки DOM
        this.init();
    }

    /**
     * Инициализация компонента
     */
    init() {
        // Получаем десктопные элементы DOM
        this.trigger = document.getElementById('project-selector-trigger');
        this.selectedProjectName = document.getElementById('selected-project-name');

        // Получаем мобильные элементы DOM
        this.triggerMobile = document.getElementById('project-selector-trigger-mobile');
        this.selectedProjectNameMobile = document.getElementById('selected-project-name-mobile');

        // Общие элементы модального окна
        this.modal = document.getElementById('project-selector-modal');
        this.overlay = document.getElementById('project-selector-overlay');
        this.searchInput = document.getElementById('project-search-input');
        this.projectsList = document.getElementById('projects-list');

        // Если элементы не найдены, выходим
        if ((!this.trigger && !this.triggerMobile) || !this.modal) {
            console.log('Селектор проектов: элементы не найдены');
            return;
        }

        // Привязываем обработчики событий
        this.bindEvents();

        // Обновляем отображение выбранного проекта при загрузке
        this.updateSelectedProjectDisplay();

        console.log('Селектор проектов инициализирован');
    }

    /**
     * Привязка обработчиков событий
     */
    bindEvents() {
        // Открытие модального окна по клику на десктопный триггер
        if (this.trigger) {
            this.trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                this.openModal();
            });
        }

        // Открытие модального окна по клику на мобильный триггер
        if (this.triggerMobile) {
            this.triggerMobile.addEventListener('click', (e) => {
                e.stopPropagation();
                this.openModal();
            });
        }

        // Закрытие по клику на overlay
        if (this.overlay) {
            this.overlay.addEventListener('click', () => this.closeModal());
        }

        // Поиск при вводе текста
        if (this.searchInput) {
            this.searchInput.addEventListener('input', (e) => {
                this.filterProjects(e.target.value);
            });
        }

        // Закрытие по клавише Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.closeModal();
            }
        });
    }

    /**
     * Открытие модального окна
     */
    async openModal() {
        if (this.isOpen) return;

        this.isOpen = true;
        this.modal.classList.remove('hidden');

        // Загружаем проекты если ещё не загружены
        if (this.projects.length === 0) {
            await this.loadProjects();
        } else {
            this.renderProjects(this.projects);
        }

        // Фокус на поле поиска
        if (this.searchInput) {
            this.searchInput.value = '';
            this.searchInput.focus();
        }
    }

    /**
     * Закрытие модального окна
     */
    closeModal() {
        if (!this.isOpen) return;

        this.isOpen = false;
        this.modal.classList.add('hidden');

        // Очищаем поле поиска
        if (this.searchInput) {
            this.searchInput.value = '';
        }
    }

    /**
     * Загрузка списка проектов через API
     */
    async loadProjects() {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoading();

        try {
            const response = await fetch('/api/projects', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            // Проверяем статус ответа
            if (!response.ok) {
                console.error('API вернул ошибку:', response.status);
                this.showError('Ошибка загрузки проектов');
                return;
            }

            const data = await response.json();

            // Поддержка обоих форматов: {success, projects} и просто массив
            let projects;
            if (Array.isArray(data)) {
                // API вернул просто массив проектов
                projects = data;
            } else if (data.success && Array.isArray(data.projects)) {
                // API вернул объект с полем projects
                projects = data.projects;
            } else {
                console.error('Неожиданный формат ответа:', data);
                this.showError('Ошибка загрузки проектов');
                return;
            }

            this.projects = projects;
            this.renderProjects(this.projects);
            console.log(`Загружено проектов: ${this.projects.length}`);
        } catch (error) {
            this.showError('Ошибка соединения с сервером');
            console.error('Ошибка при загрузке проектов:', error);
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Фильтрация проектов по поисковому запросу
     * @param {string} query - Поисковый запрос
     */
    filterProjects(query) {
        const searchQuery = query.toLowerCase().trim();

        if (!searchQuery) {
            this.renderProjects(this.projects);
            return;
        }

        const filtered = this.projects.filter(project => {
            const name = (project.name || '').toLowerCase();
            const url = (project.url || '').toLowerCase();
            return name.includes(searchQuery) || url.includes(searchQuery);
        });

        this.renderProjects(filtered);
    }

    /**
     * Отрисовка списка проектов
     * @param {Array} projects - Массив проектов для отображения
     */
    renderProjects(projects) {
        if (!this.projectsList) return;

        // Добавляем ссылку на создание проекта (всегда первая в списке)
        const createProjectHtml = `
            <a href="/projects/create" class="create-project-link">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="12" y1="5" x2="12" y2="19"></line>
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
                Создать проект
            </a>
        `;

        if (projects.length === 0) {
            this.projectsList.innerHTML = createProjectHtml + `
                <div class="project-selector-empty">
                    Проекты не найдены
                </div>
            `;
            return;
        }

        // Получаем текущий выбранный проект
        const selectedId = this.getSelectedProjectId();

        const projectsHtml = projects.map(project => `
            <div class="project-selector-item ${project.id == selectedId ? 'active' : ''}" 
                 data-id="${project.id}" 
                 data-name="${this.escapeHtml(project.name)}">
                <div class="project-selector-item-name">${this.escapeHtml(project.name)}</div>
                <div class="project-selector-item-url">${this.escapeHtml(project.url)}</div>
            </div>
        `).join('');

        this.projectsList.innerHTML = createProjectHtml + projectsHtml;

        // Привязываем обработчики кликов на элементы проектов (исключая ссылку на создание)
        this.projectsList.querySelectorAll('.project-selector-item:not(.create-project-link)').forEach(item => {
            item.addEventListener('click', () => {
                const id = item.dataset.id;
                const name = item.dataset.name;
                this.selectProject(id, name);
            });
        });
    }

    /**
     * Выбор проекта
     * @param {string|number} projectId - ID проекта
     * @param {string} projectName - Название проекта
     */
    selectProject(projectId, projectName) {
        try {
            // Сохраняем в localStorage
            localStorage.setItem('selectedProjectId', projectId);
            localStorage.setItem('selectedProjectName', projectName);

            console.log(`Выбран проект: ID=${projectId}, Name=${projectName}`);

            // Редирект на страницу проверки позиций
            window.location.href = `/projects/${projectId}/positions`;
        } catch (error) {
            console.error('Ошибка при выборе проекта:', error);
        }
    }

    /**
     * Получение ID выбранного проекта из localStorage
     * @returns {string|null}
     */
    getSelectedProjectId() {
        try {
            return localStorage.getItem('selectedProjectId');
        } catch (error) {
            return null;
        }
    }

    /**
     * Обновление отображения выбранного проекта в хедере и мобильной панели
     */
    updateSelectedProjectDisplay() {
        // Проверяем наличие хотя бы одного элемента
        if (!this.selectedProjectName && !this.selectedProjectNameMobile) return;

        try {
            let projectName = localStorage.getItem('selectedProjectName');
            const projectId = localStorage.getItem('selectedProjectId');

            // Если ID есть, а названия нет - пробуем найти в уже загруженных проектах
            if (projectId && projectId !== 'all' && !projectName && this.projects.length > 0) {
                const project = this.projects.find(p => p.id == projectId);
                if (project) {
                    projectName = project.name;
                    localStorage.setItem('selectedProjectName', projectName);
                }
            }

            let displayText = 'Выберите проект';
            if (projectId === 'all') {
                displayText = 'Выберите проект';
            } else if (projectName && projectId) {
                displayText = projectName;
            } else if (projectId) {
                // Если есть только ID, а названия нет и проекты еще не загружены
                displayText = 'Загрузка...';
                // Загружаем проекты, чтобы получить название
                if (this.projects.length === 0 && !this.isLoading) {
                    this.loadProjects().then(() => this.updateSelectedProjectDisplay());
                }
            }

            // Обновляем десктопную версию
            if (this.selectedProjectName) {
                this.selectedProjectName.textContent = displayText;
            }

            // Обновляем мобильную версию
            if (this.selectedProjectNameMobile) {
                this.selectedProjectNameMobile.textContent = displayText;
            }
        } catch (error) {
            const fallbackText = 'Выберите проект';
            if (this.selectedProjectName) {
                this.selectedProjectName.textContent = fallbackText;
            }
            if (this.selectedProjectNameMobile) {
                this.selectedProjectNameMobile.textContent = fallbackText;
            }
        }
    }

    /**
     * Показ индикатора загрузки
     */
    showLoading() {
        if (this.projectsList) {
            this.projectsList.innerHTML = `
                <div class="project-selector-loading">
                    <div class="spinner"></div>
                    <span>Загрузка проектов...</span>
                </div>
            `;
        }
    }

    /**
     * Показ сообщения об ошибке
     * @param {string} message - Текст ошибки
     */
    showError(message) {
        if (this.projectsList) {
            this.projectsList.innerHTML = `
                <div class="project-selector-error">
                    ${this.escapeHtml(message)}
                </div>
            `;
        }
    }

    /**
     * Экранирование HTML
     * @param {string} str - Строка для экранирования
     * @returns {string}
     */
    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', () => {
    window.projectSelector = new ProjectSelector();

    // Слушаем изменения в localStorage из других вкладок
    window.addEventListener('storage', (e) => {
        if (e.key === 'selectedProjectId' || e.key === 'selectedProjectName') {
            if (window.projectSelector) {
                window.projectSelector.updateSelectedProjectDisplay();
            }
        }
    });
});
