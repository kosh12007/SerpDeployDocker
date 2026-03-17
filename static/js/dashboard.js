/**
 * Dashboard JavaScript
 * Управление дашбордом: графики, статистика, выбор проекта/варианта/дат
 */
document.addEventListener('DOMContentLoaded', function () {
    const ctx = document.getElementById('topDistributionChart');
    const projectSelector = document.getElementById('dashboard-project-selector');
    const variantSelector = document.getElementById('dashboard-variant-selector');
    const dateBtn1 = document.getElementById('dashboard-date-btn-1');
    const dateBtn2 = document.getElementById('dashboard-date-btn-2');
    const dateText1 = document.getElementById('dashboard-date-text-1');
    const dateText2 = document.getElementById('dashboard-date-text-2');

    if (!ctx || !projectSelector) return;

    let distributionChart;
    let availableDates = []; // Доступные даты для текущего варианта
    let currentVariantId = null;
    let dateFrom = null; // Базовая дата (с чем сравниваем)
    let dateTo = null;   // Целевая дата (что сравниваем)

    // Инициализация графика
    function initChart(data) {
        if (distributionChart) {
            distributionChart.destroy();
        }

        const chartData = {
            labels: ['ТОП-1', 'ТОП-3', 'ТОП-10', 'ТОП-30', 'ТОП-100'],
            datasets: [{
                label: 'Запросы',
                data: [
                    data.top_1 || 0,
                    data.top_3 || 0,
                    data.top_10 || 0,
                    data.top_30 || 0,
                    data.top_100 || 0
                ],
                backgroundColor: [
                    'rgba(95, 87, 255, 0.8)',
                    'rgba(99, 102, 241, 0.8)',
                    'rgba(139, 92, 246, 0.8)',
                    'rgba(236, 72, 153, 0.8)',
                    'rgba(244, 63, 94, 0.8)'
                ],
                borderWidth: 0,
                borderRadius: 8,
                barThickness: 32
            }]
        };

        distributionChart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1f2937',
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(156, 163, 175, 0.1)' },
                        ticks: { stepSize: 1, color: '#9ca3af' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#9ca3af' }
                    }
                }
            }
        });
    }

    /**
     * Обновление индикатора разницы ТОП-ов
     * @param {string} topId - ID элемента (top-1, top-3, и т.д.)
     * @param {number} diff - Разница с базовой датой
     */
    function updateDiffIndicator(topId, diff) {
        const diffEl = document.getElementById(`${topId}-diff`);
        if (!diffEl) return;

        const arrowEl = diffEl.querySelector('.diff-arrow');
        const valueEl = diffEl.querySelector('.diff-value');

        if (diff === 0 || diff === undefined || diff === null) {
            // Нет изменений - скрываем индикатор
            diffEl.classList.add('hidden');
            return;
        }

        diffEl.classList.remove('hidden');

        if (diff > 0) {
            // Рост - зеленая стрелка вверх
            arrowEl.textContent = '↑';
            arrowEl.className = 'diff-arrow text-green-500 font-bold';
            valueEl.textContent = `+${diff}`;
            valueEl.className = 'diff-value text-green-500';
        } else {
            // Падение - красная стрелка вниз
            arrowEl.textContent = '↓';
            arrowEl.className = 'diff-arrow text-red-500 font-bold';
            valueEl.textContent = `${diff}`;
            valueEl.className = 'diff-value text-red-500';
        }
    }

    /**
     * Скрытие всех индикаторов разницы
     */
    function hideAllDiffIndicators() {
        ['top-1', 'top-3', 'top-10', 'top-30', 'top-100'].forEach(topId => {
            const diffEl = document.getElementById(`${topId}-diff`);
            if (diffEl) diffEl.classList.add('hidden');
        });
    }

    // Обновление числовых показателей и индикаторов разницы
    function updateStatCards(data) {
        const totalProjectsEl = document.getElementById('stat-value-мои-проекты');
        const totalQueriesEl = document.getElementById('stat-value-всего-запросов');
        const unassignedQueriesEl = document.getElementById('stat-desc-всего-запросов');
        const limitsEl = document.getElementById('stat-value-лимиты');

        if (totalProjectsEl) totalProjectsEl.textContent = data.total_projects;
        if (totalQueriesEl) totalQueriesEl.textContent = data.total_queries;
        if (unassignedQueriesEl) unassignedQueriesEl.textContent = 'из них ' + data.unassigned_queries + ' без групп';
        if (limitsEl) limitsEl.textContent = data.limits;

        // Обновляем значения ТОП-ов через ID
        const top1Value = document.getElementById('top-1-value');
        const top3Value = document.getElementById('top-3-value');
        const top10Value = document.getElementById('top-10-value');
        const top30Value = document.getElementById('top-30-value');
        const top100Value = document.getElementById('top-100-value');

        if (top1Value) top1Value.textContent = data.top_1;
        if (top3Value) top3Value.textContent = data.top_3;
        if (top10Value) top10Value.textContent = data.top_10;
        if (top30Value) top30Value.textContent = data.top_30;
        if (top100Value) top100Value.textContent = data.top_100;

        // Обновляем индикаторы разницы (только если есть обе даты)
        if (dateFrom && dateTo) {
            updateDiffIndicator('top-1', data.top_1_diff);
            updateDiffIndicator('top-3', data.top_3_diff);
            updateDiffIndicator('top-10', data.top_10_diff);
            updateDiffIndicator('top-30', data.top_30_diff);
            updateDiffIndicator('top-100', data.top_100_diff);
        } else {
            // Скрываем индикаторы если не выбраны обе даты
            hideAllDiffIndicators();
        }
    }

    /**
     * Загрузка статистики с учетом выбранного проекта, варианта и дат
     */
    function refreshStats(projectId, variantId = null, dateFromVal = null, dateToVal = null) {
        let url = `/api/dashboard/stats?project_id=${projectId || 'all'}`;

        if (variantId) {
            url += `&variant_id=${variantId}`;
        }
        if (dateFromVal) {
            url += `&date_from=${dateFromVal}`;
        }
        if (dateToVal) {
            url += `&date_to=${dateToVal}`;
        }

        fetch(url)
            .then(response => response.json())
            .then(data => {
                initChart(data);
                updateStatCards(data);
                const balanceEl = document.getElementById('dashboard-balance');
                if (balanceEl && data.balance !== undefined) {
                    balanceEl.textContent = data.balance;
                }
            })
            .catch(error => console.error('Ошибка при загрузке статистики:', error));
    }

    /**
     * Загрузка вариантов парсинга для проекта
     */
    function loadVariants(projectId) {
        if (!variantSelector) return;

        // Очищаем селект
        variantSelector.innerHTML = '<option value="">Вариант парсинга</option>';
        variantSelector.disabled = true;
        currentVariantId = null;
        dateFrom = null;
        dateTo = null;

        // Отключаем кнопки дат
        if (dateBtn1) dateBtn1.disabled = true;
        if (dateBtn2) dateBtn2.disabled = true;
        if (dateText1) dateText1.textContent = 'Дата 1';
        if (dateText2) dateText2.textContent = 'Дата 2';
        hideAllDiffIndicators();

        if (!projectId || projectId === 'all') {
            return;
        }

        fetch(`/api/projects/${projectId}/variants`)
            .then(response => response.json())
            .then(variants => {
                if (variants && variants.length > 0) {
                    const savedVariant = localStorage.getItem(`selected_variant_${projectId}`);

                    variants.forEach(variant => {
                        const option = document.createElement('option');
                        option.value = variant.id;
                        option.textContent = variant.full_text || variant.name;
                        if (savedVariant && variant.id.toString() === savedVariant) {
                            option.selected = true;
                        }
                        variantSelector.appendChild(option);
                    });

                    variantSelector.disabled = false;

                    // Если был сохранен вариант, загружаем даты для него
                    if (savedVariant) {
                        currentVariantId = parseInt(savedVariant);
                        loadAvailableDates(projectId, currentVariantId);
                    }
                }
            })
            .catch(error => console.error('Ошибка при загрузке вариантов:', error));
    }

    /**
     * Загрузка доступных дат для варианта парсинга
     */
    function loadAvailableDates(projectId, variantId) {
        if (!dateBtn1 || !dateBtn2 || !variantId) return;

        fetch(`/api/projects/${projectId}/available-dates?variant_id=${variantId}`)
            .then(response => response.json())
            .then(dates => {
                availableDates = dates || [];

                if (availableDates.length > 0) {
                    dateBtn1.disabled = false;
                    dateBtn2.disabled = false;

                    // Проверяем сохраненные даты
                    const savedDateFrom = localStorage.getItem(`selected_date_from_${projectId}_${variantId}`);
                    const savedDateTo = localStorage.getItem(`selected_date_to_${projectId}_${variantId}`);

                    if (savedDateFrom && availableDates.includes(savedDateFrom)) {
                        dateFrom = savedDateFrom;
                        updateDateButtonText(dateText1, dateFrom);
                    }

                    if (savedDateTo && availableDates.includes(savedDateTo)) {
                        dateTo = savedDateTo;
                        updateDateButtonText(dateText2, dateTo);
                    }

                    // Обновляем статистику
                    refreshStats(projectId, variantId, dateFrom, dateTo);
                } else {
                    dateBtn1.disabled = true;
                    dateBtn2.disabled = true;
                    if (dateText1) dateText1.textContent = 'Нет данных';
                    if (dateText2) dateText2.textContent = 'Нет данных';
                }
            })
            .catch(error => console.error('Ошибка при загрузке доступных дат:', error));
    }

    /**
     * Обновление текста кнопки даты
     */
    function updateDateButtonText(textEl, dateStr) {
        if (!textEl || !dateStr) return;
        // Преобразуем YYYY-MM-DD в DD.MM.YYYY
        const parts = dateStr.split('-');
        if (parts.length === 3) {
            textEl.textContent = `${parts[2]}.${parts[1]}.${parts[0]}`;
        } else {
            textEl.textContent = dateStr;
        }
    }

    /**
     * Показ календаря с доступными датами
     * @param {number} dateNumber - 1 или 2 (какую дату выбираем)
     */
    function showDatePicker(dateNumber) {
        const projectId = projectSelector.value;
        if (!currentVariantId || availableDates.length === 0) return;

        // Текущее выбранное значение
        const currentValue = dateNumber === 1 ? dateFrom : dateTo;

        // Элемент, к которому привязываем календарь
        const triggerElement = dateNumber === 1 ? dateBtn1 : dateBtn2;

        // Создаем временный input для Flatpickr
        const tempInput = document.createElement('input');
        tempInput.type = 'text';
        // Используем fixed чтобы не влиять на скролл, и прозрачность вместо visibility:hidden
        tempInput.style.position = 'fixed';
        tempInput.style.opacity = '0';
        tempInput.style.top = '0';
        tempInput.style.left = '0';
        tempInput.style.pointerEvents = 'none';
        document.body.appendChild(tempInput);

        const fp = flatpickr(tempInput, {
            mode: 'single',
            dateFormat: 'Y-m-d',
            defaultDate: currentValue || (dateNumber === 1 ? availableDates[availableDates.length - 1] : availableDates[0]),
            locale: 'ru',
            enable: availableDates,
            disableMobile: true, // Принудительно используем десктопную версию для корректного позиционирования
            inline: false,
            positionElement: triggerElement, // Привязываем позицию к кнопке
            appendTo: document.body,
            onChange: function (selectedDates, dateStr) {
                if (dateStr) {
                    if (dateNumber === 1) {
                        dateFrom = dateStr;
                        localStorage.setItem(`selected_date_from_${projectId}_${currentVariantId}`, dateStr);
                        updateDateButtonText(dateText1, dateStr);
                    } else {
                        dateTo = dateStr;
                        localStorage.setItem(`selected_date_to_${projectId}_${currentVariantId}`, dateStr);
                        updateDateButtonText(dateText2, dateStr);
                    }

                    // Обновляем статистику
                    refreshStats(projectId, currentVariantId, dateFrom, dateTo);
                }
                fp.close();
            },
            onClose: function () {
                setTimeout(() => {
                    tempInput.remove();
                    fp.destroy();
                }, 100);
            }
        });

        fp.open();
    }

    // Загрузка списка проектов
    function loadProjects() {
        fetch('/api/dashboard/projects')
            .then(response => response.json())
            .then(projects => {
                const currentSelected = localStorage.getItem('selectedProjectId');
                projects.forEach(project => {
                    const option = document.createElement('option');
                    option.value = project.id;
                    option.textContent = project.name;
                    if (currentSelected && project.id.toString() === currentSelected) {
                        option.selected = true;
                    }
                    projectSelector.appendChild(option);
                });

                // Начальный запуск после загрузки списка
                const initialProject = projectSelector.value;

                // Загружаем варианты для выбранного проекта
                if (initialProject && initialProject !== 'all') {
                    loadVariants(initialProject);
                } else {
                    refreshStats(initialProject);
                }
            })
            .catch(error => console.error('Ошибка при загрузке проектов:', error));
    }

    // Обработка смены проекта
    projectSelector.addEventListener('change', function () {
        const projectId = this.value;
        const projectName = this.options[this.selectedIndex].text;

        localStorage.setItem('selectedProjectId', projectId);
        if (projectId === 'all') {
            localStorage.removeItem('selectedProjectName');
        } else {
            localStorage.setItem('selectedProjectName', projectName);
        }

        // Уведомляем селектор в хедере, если он есть
        if (window.projectSelector) {
            window.projectSelector.updateSelectedProjectDisplay();
        }

        // Загружаем варианты для нового проекта
        loadVariants(projectId);

        // Обновляем статистику без варианта и дат
        refreshStats(projectId);
    });

    // Обработка смены варианта парсинга
    if (variantSelector) {
        variantSelector.addEventListener('change', function () {
            const projectId = projectSelector.value;
            const variantId = this.value;

            if (variantId) {
                currentVariantId = parseInt(variantId);
                localStorage.setItem(`selected_variant_${projectId}`, variantId);

                // Сбрасываем даты
                dateFrom = null;
                dateTo = null;
                if (dateText1) dateText1.textContent = 'Дата 1';
                if (dateText2) dateText2.textContent = 'Дата 2';
                hideAllDiffIndicators();

                // Загружаем доступные даты для выбранного варианта
                loadAvailableDates(projectId, currentVariantId);
            } else {
                currentVariantId = null;
                dateFrom = null;
                dateTo = null;
                if (dateBtn1) dateBtn1.disabled = true;
                if (dateBtn2) dateBtn2.disabled = true;
                if (dateText1) dateText1.textContent = 'Дата 1';
                if (dateText2) dateText2.textContent = 'Дата 2';
                hideAllDiffIndicators();
                refreshStats(projectId);
            }
        });
    }

    // Обработка клика по кнопкам дат
    if (dateBtn1) {
        dateBtn1.addEventListener('click', () => showDatePicker(1));
    }
    if (dateBtn2) {
        dateBtn2.addEventListener('click', () => showDatePicker(2));
    }

    // Инициализация
    loadProjects();

    // Функция получения баланса из localStorage
    function getBalance() {
        const savedBalance = localStorage.getItem('balance') || 'N/A';
        console.log('Сохраненный баланс:', savedBalance);

        const balanceEl = document.getElementById('dashboard-balance');
        if (balanceEl) {
            balanceEl.textContent = savedBalance;
        }
    }
    getBalance();

    // Обработка кнопки обновления баланса
    const refreshBtn = document.getElementById('refresh-dashboard-balance');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function () {
            this.classList.add('animate-spin');
            getBalance();
            setTimeout(() => this.classList.remove('animate-spin'), 1000);
        });
    }
});
