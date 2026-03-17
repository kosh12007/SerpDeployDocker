document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('uniquenessForm');
    const textInput = document.getElementById('textInput');
    const charCount = document.getElementById('charCount');
    const checkButton = document.getElementById('checkButton');
    const resetButton = document.getElementById('resetButton');
    const textHighlightView = document.getElementById('textHighlightView');
    const uniquenessResults = document.getElementById('uniquenessResults');
    const scoreBadge = document.getElementById('scoreBadge');
    const checkedShingles = document.getElementById('checkedShingles');
    const nonUniqueShingles = document.getElementById('nonUniqueShingles');
    const totalShingles = document.getElementById('totalShingles');
    const matchesContainer = document.getElementById('matchesContainer');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const loadingMessage = document.getElementById('loadingMessage');
    const loadingProgressBlock = document.getElementById('loadingProgressBlock');
    const errorContainer = document.getElementById('errorContainer');

    // Модалка лимитов
    const limitsConfirmModal = document.getElementById('limitsConfirmModal');
    const estimatedCostSpan = document.getElementById('estimatedCost');
    const totalShinglesSpan = document.getElementById('totalShingles');
    const cachedShinglesSpan = document.getElementById('cachedShingles');
    const cacheStatsContainer = document.getElementById('cacheStats');
    const currentUserLimitsSpan = document.getElementById('currentUserLimits');
    const remainingLimitsSpan = document.getElementById('remainingLimits');
    const cancelLimitsBtn = document.getElementById('cancelLimitsBtn');
    const confirmLimitsBtn = document.getElementById('confirmLimitsBtn');

    const saveStatus = document.getElementById('saveStatus');
    const highlightLegend = document.getElementById('highlightLegend');
    const legendBox = document.getElementById('legendBox');
    const highlightAllBtn = document.getElementById('highlightAllBtn');
    const expandMatchesContainer = document.getElementById('expandMatchesContainer');

    // Элементы для Этап 1
    const stage1Results = document.getElementById('stage1Results');
    const stage1ScoreValue = document.getElementById('stage1ScoreValue');
    const stage1ScoreText = document.getElementById('stage1ScoreText');
    const highlightStage1Btn = document.getElementById('highlightStage1Btn');

    // Элементы для Этап 2
    const stage2Results = document.getElementById('stage2Results');
    const stage2ScoreValue = document.getElementById('stage2ScoreValue');
    const stage2ScoreText = document.getElementById('stage2ScoreText');
    const highlightStage2Btn = document.getElementById('highlightStage2Btn');
    const verifiedUrlLink = document.getElementById('verifiedUrlLink');
    const verificationError = document.getElementById('verificationError');

    const copyReportBtn = document.getElementById('copyReportBtn');
    const downloadTxtBtn = document.getElementById('downloadTxtBtn');
    const downloadJsonBtn = document.getElementById('downloadJsonBtn');

    let lastResultData = null;

    let currentMatches = [];        // Совпадения Этап 1 (API)
    let verifiedMatches = [];       // Совпадения Этап 2 (контент)
    let domainVisibility = {};      // domain -> boolean
    let originalTextContent = '';
    let stage1HighlightActive = false;
    let stage2HighlightActive = false;
    let isResultsExpanded = false;   // Состояние развернутого списка результатов

    // Загрузка сохраненного текста
    const savedText = localStorage.getItem('uniqueness_checker_text');
    if (savedText) {
        textInput.value = savedText;
        charCount.textContent = savedText.length;
        originalTextContent = savedText; // Restore original text content for highlight view
    }

    // Восстановление результата проверки
    const savedResultJSON = localStorage.getItem('uniqueness_checker_result');
    if (savedResultJSON) {
        try {
            const savedData = JSON.parse(savedResultJSON);
            if (savedData && savedData.text === textInput.value && textInput.value.length > 0) {
                currentMatches = savedData.matches || [];
                displayResults(savedData);
            }
        } catch (e) {
            console.error('Error parsing saved result', e);
        }
    }

    // Счетчик символов + статус сохранения
    let saveTimeout;
    textInput.addEventListener('input', function () {
        charCount.textContent = this.value.length;

        // Сохраняем в localStorage
        localStorage.setItem('uniqueness_checker_text', this.value);

        // Эмуляция "Текст сохранен" как на скриншоте (теперь это правда)
        saveStatus.classList.remove('opacity-0');
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(() => {
            saveStatus.classList.add('opacity-0');
        }, 2000);
    });

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        const text = textInput.value.trim();
        if (text.length < 50) {
            showError('Текст слишком короткий (минимум 50 символов).');
            return;
        }

        originalTextContent = text;

        // Подготовка интерфейса
        errorContainer.classList.add('hidden');
        uniquenessResults.classList.add('hidden');

        // Шаг 1: Оценка стоимости (лимитов)
        checkButton.disabled = true;
        const originalBtnText = checkButton.innerHTML;
        checkButton.innerHTML = '<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2 inline-block"></div> Оцениваем...';

        fetch('/uniqueness/estimate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
            },
            body: JSON.stringify({ text_input: text })
        })
            .then(res => res.json())
            .then(data => {
                if (data.error) throw new Error(data.error);

                if (data.total_shingles === 0) {
                    showError('Текст слишком короткий для формирования шинглов.');
                    resetCheckButton();
                    return;
                }

                // Показываем модалку подтверждения
                estimatedCostSpan.textContent = data.cost;

                if (data.total_shingles !== undefined) {
                    totalShinglesSpan.textContent = data.total_shingles;
                    cachedShinglesSpan.textContent = data.cached_shingles || 0;
                    cacheStatsContainer.classList.remove('hidden');
                } else {
                    cacheStatsContainer.classList.add('hidden');
                }

                currentUserLimitsSpan.textContent = data.user_limits;
                const remaining = data.user_limits - data.cost;
                remainingLimitsSpan.textContent = remaining;

                if (remaining < 0) {
                    remainingLimitsSpan.classList.add('text-red-500');
                    confirmLimitsBtn.disabled = true;
                    confirmLimitsBtn.classList.add('opacity-50', 'cursor-not-allowed');
                    confirmLimitsBtn.textContent = 'Недостаточно лимитов';
                } else {
                    remainingLimitsSpan.classList.remove('text-red-500');
                    confirmLimitsBtn.disabled = false;
                    confirmLimitsBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                    confirmLimitsBtn.textContent = 'Продолжить';
                }

                limitsConfirmModal.classList.remove('hidden');
            })
            .catch(err => {
                showError('Ошибка при расчете стоимости: ' + err.message);
                resetCheckButton();
            });
    });

    function resetCheckButton() {
        checkButton.disabled = false;
        checkButton.innerHTML = 'Проверить уникальность';
    }

    cancelLimitsBtn.addEventListener('click', () => {
        limitsConfirmModal.classList.add('hidden');
        resetCheckButton();
    });

    confirmLimitsBtn.addEventListener('click', () => {
        limitsConfirmModal.classList.add('hidden');
        startCheck();
    });

    function startCheck() {
        const text = textInput.value.trim();
        const verifyContent = document.getElementById('verifyContent').checked;

        loadingOverlay.classList.remove('hidden');
        if (loadingMessage) loadingMessage.textContent = 'Проверка уникальности...';
        if (loadingProgressBlock) loadingProgressBlock.classList.remove('hidden');

        fetch('/uniqueness/check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
            },
            body: JSON.stringify({
                text_input: text,
                verify_content: verifyContent
            })
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    pollTaskStatus(data.task_id);
                } else {
                    throw new Error(data.error || 'Произошла ошибка при запуске проверки.');
                }
            })
            .catch(err => {
                loadingOverlay.classList.add('hidden');
                resetCheckButton();
                showError(err.message);
            });
    }

    function pollTaskStatus(taskId) {
        const progressPercent = document.getElementById('progressPercent');
        const progressCount = document.getElementById('progressCount');

        const interval = setInterval(() => {
            fetch(`/uniqueness/status/${taskId}`)
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'completed') {
                        if (data.result) {
                            clearInterval(interval);
                            loadingOverlay.classList.add('hidden');
                            checkButton.disabled = false;
                            currentMatches = data.result.matches || [];
                            displayResults(data.result);
                            updateHistoryRow(taskId, data);
                        } else {
                            // Если статус 'completed', но результата еще нет в ответе, подождем еще цикл
                            console.warn('Task completed but result is missing. Retrying poll...', taskId);
                        }
                    } else if (data.status === 'error') {
                        clearInterval(interval);
                        loadingOverlay.classList.add('hidden');
                        checkButton.disabled = false;
                        showError(data.error || 'Ошибка при выполнении задачи.');
                        updateHistoryRow(taskId, data);
                    } else {
                        // Обновляем прогресс
                        if (progressPercent && data.progress_total > 0) {
                            const percent = Math.round((data.progress_current / data.progress_total) * 100);
                            progressPercent.textContent = `${percent}%`;
                            updateHistoryRow(taskId, data, percent);
                        }
                        if (progressCount) {
                            progressCount.textContent = `(${data.progress_current} / ${data.progress_total})`;
                        }
                    }
                })
                .catch(err => {
                    clearInterval(interval);
                    loadingOverlay.classList.add('hidden');
                    checkButton.disabled = false;
                    showError('Ошибка при получении статуса: ' + err.message);
                });
        }, 1500);
    }

    resetButton.addEventListener('click', function () {
        textInput.value = '';
        textInput.classList.remove('hidden');
        textHighlightView.classList.add('hidden');
        uniquenessResults.classList.add('hidden');
        resetButton.classList.add('hidden');
        checkButton.classList.remove('hidden');
        charCount.textContent = '0';
        errorContainer.classList.add('hidden');
        highlightLegend.classList.add('hidden');
    });

    highlightAllBtn.addEventListener('click', function () {
        // Если все видны -> выключаем все. Иначе -> включаем все.
        const allVisible = Object.values(domainVisibility).length > 0 && Object.values(domainVisibility).every(v => v);
        const targetValue = !allVisible;

        Object.keys(domainVisibility).forEach(d => domainVisibility[d] = targetValue);
        stage1HighlightActive = targetValue;

        // Если включаем этап 1, выключаем этап 2
        if (targetValue) {
            stage2HighlightActive = false;
            updateStage2UI();
        }

        updateStage1UI();
        applyAllHighlights();
        renderMatches();
    });

    // Кнопка подсветки Этап 1
    highlightStage1Btn.addEventListener('click', function () {
        stage1HighlightActive = !stage1HighlightActive;

        // Взаимоисключение: выключаем этап 2
        if (stage1HighlightActive) {
            stage2HighlightActive = false;
            updateStage2UI();

            // Если ни один домен не выбран, выбираем все
            const anySelected = Object.values(domainVisibility).some(v => v);
            if (!anySelected) {
                Object.keys(domainVisibility).forEach(d => domainVisibility[d] = true);
            }
        }

        updateStage1UI();
        applyAllHighlights();
        renderMatches();
    });

    // Кнопка подсветки Этап 2
    highlightStage2Btn.addEventListener('click', function () {
        stage2HighlightActive = !stage2HighlightActive;

        // Взаимоисключение: выключаем этап 1
        if (stage2HighlightActive) {
            stage1HighlightActive = false;
            // Синхронизируем domainVisibility (выключаем все домены)
            // Object.keys(domainVisibility).forEach(d => domainVisibility[d] = false);
            updateStage1UI();
        }

        updateStage2UI();
        applyAllHighlights();
        renderMatches();
    });

    function updateStage1UI() {
        const btnText = highlightStage1Btn.querySelector('span');
        if (btnText) {
            btnText.textContent = stage1HighlightActive ? 'Скрыть' : 'Подсветить';
        }
        updateHighlightAllBtnText();
        updateLegendColor();
    }

    function updateStage2UI() {
        const btnText = highlightStage2Btn.querySelector('span');
        if (btnText) {
            btnText.textContent = stage2HighlightActive ? 'Скрыть' : 'Подсветить';
        }
        updateLegendColor();
    }

    function updateLegendColor() {
        if (!legendBox) return;

        // Если активен этап 2 - голубой, иначе (или если этап 1/ничего не выбрано) - фиолетовый
        if (stage2HighlightActive) {
            legendBox.classList.remove('stage1');
            legendBox.classList.add('stage2');
        } else {
            legendBox.classList.remove('stage2');
            legendBox.classList.add('stage1');
        }

        // Скрываем легенду если ничего не выбрано (опционально, но логично)
        const isAnythingActive = stage1HighlightActive || stage2HighlightActive || Object.values(domainVisibility).some(v => v);
        highlightLegend.classList.toggle('hidden', !isAnythingActive);
    }

    // --- Экспорт ---
    if (copyReportBtn) {
        copyReportBtn.addEventListener('click', () => {
            if (!lastResultData) return;
            const text = formatReportText(lastResultData);
            navigator.clipboard.writeText(text).then(() => {
                const originalText = copyReportBtn.innerHTML;
                copyReportBtn.textContent = 'Скопировано!';
                setTimeout(() => copyReportBtn.innerHTML = originalText, 2000);
            }).catch(err => {
                console.error('Failed to copy: ', err);
                alert('Не удалось скопировать в буфер обмена');
            });
        });
    }

    if (downloadTxtBtn) {
        downloadTxtBtn.addEventListener('click', () => {
            if (!lastResultData) return;
            const text = formatReportText(lastResultData);
            downloadFile(text, 'uniqueness_report.txt', 'text/plain');
        });
    }

    if (downloadJsonBtn) {
        downloadJsonBtn.addEventListener('click', () => {
            if (!lastResultData) return;
            // Добавляем текст в JSON для полноты
            const dataToSave = { ...lastResultData, text: originalTextContent };
            downloadFile(JSON.stringify(dataToSave, null, 2), 'uniqueness_report.json', 'application/json');
        });
    }

    function formatReportText(data) {
        const date = new Date().toLocaleString('ru-RU');
        let report = `Отчет об уникальности текста\nДата: ${date}\n\n`;

        const stage1Score = data.original_score !== undefined ? data.original_score : data.score;
        report += `===== Этап 1: Поиск по API =====\n`;
        report += `Уникальность: ${stage1Score}%\n`;
        report += `Найдено совпадений: ${currentMatches.length}\n`;

        const domains = getDomainsFromMatches(currentMatches);
        if (domains.length > 0) {
            report += `\nИсточники (Топ ${Math.min(domains.length, 10)}):\n`;
            domains.slice(0, 10).forEach(d => {
                report += `- ${d.url} (${d.percent}%)\n`;
            });
        }
        report += '\n';

        if (data.verified_url) {
            report += `===== Этап 2: Верификация контента =====\n`;
            report += `Проверенный URL: ${data.verified_url}\n`;
            report += `Уникальность (верифицированная): ${data.verified_score}%\n`;
        } else if (data.verification_error) {
            report += `===== Этап 2: Ошибка верификации =====\n${data.verification_error}\n`;
        }

        return report;
    }

    function downloadFile(content, filename, contentType) {
        const a = document.createElement('a');
        const file = new Blob([content], { type: contentType });
        a.href = URL.createObjectURL(file);
        a.download = filename;
        a.click();
        URL.revokeObjectURL(a.href);
    }


    // Применяем подсветку для обоих этапов
    function applyAllHighlights() {
        let html = '';
        if (!originalTextContent) return;

        const paragraphs = originalTextContent.split('\n');

        html = paragraphs.map(paragraph => {
            let pContent = escapeHtml(paragraph);

            // --- Подсветка Этап 1 (фиолетовый) ---
            if (stage1HighlightActive && currentMatches.length > 0) {
                const stage1Fragments = [];
                currentMatches.forEach(match => {
                    const isVisible = match.urls.some(url => domainVisibility[url]);
                    if (isVisible && match.original) {
                        stage1Fragments.push(match.original);
                    }
                });

                if (stage1Fragments.length > 0) {
                    pContent = applyHighlightToText(pContent, stage1Fragments, 'match-highlight-stage1');
                }
            }

            // --- Подсветка Этап 2 (голубой) ---
            if (stage2HighlightActive && verifiedMatches.length > 0) {
                pContent = applyHighlightToText(pContent, verifiedMatches, 'match-highlight-stage2');
            }

            return `<p class="mb-2">${pContent}</p>`;
        }).join('');

        textHighlightView.innerHTML = html;
    }

    // Применяет подсветку к фрагментам в тексте параграфа
    function applyHighlightToText(text, fragments, cssClass) {
        // Сортируем фрагменты по длине (сначала длинные) для корректной вложенной подсветки
        const uniqueFragments = [...new Set(fragments)].sort((a, b) => b.length - a.length);

        if (uniqueFragments.length === 0) return text;

        const regexParts = uniqueFragments.map(fragment => {
            // Разбиваем фрагмент на слова (он уже состоит из слов и пробелов согласно логике бэкенда)
            const words = fragment.trim().split(/\s+/);
            if (words.length === 0) return "";

            // Экранируем слова и соединяем их паттерном, который допускает любые несловесные символы между ними
            return words.map(word => escapeRegex(word)).join('[\\s\\W]*');
        }).filter(p => p !== "");

        if (regexParts.length === 0) return text;

        // Используем 'gi' флаг для глобального поиска без учета регистра
        const combinedRegex = new RegExp(`(${regexParts.join('|')})`, 'gi');

        return text.replace(combinedRegex, `<span class="${cssClass}">$1</span>`);
    }

    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function updateHighlightAllBtnText() {
        const anyMatches = Object.values(domainVisibility).length > 0;
        const allVisible = anyMatches && Object.values(domainVisibility).every(v => v);
        const btnText = highlightAllBtn.querySelector('span');
        if (btnText) {
            btnText.textContent = allVisible ? 'Скрыть все' : 'Подсветить все';
        }
    }

    function displayResults(data) {
        if (!data) return;
        uniquenessResults.classList.remove('hidden');
        highlightLegend.classList.remove('hidden');

        // Сохраняем результат
        lastResultData = data;
        // Добавляем текст в данные для сохранения, чтобы проверять валидность при загрузке
        const dataToSave = { ...data, text: originalTextContent };
        localStorage.setItem('uniqueness_checker_result', JSON.stringify(dataToSave));

        // Сброс состояния подсветки
        stage1HighlightActive = false;
        stage2HighlightActive = false;
        isResultsExpanded = false; // Сбрасываем состояние развернутого списка
        verifiedMatches = data.verified_matches || [];

        // ====== Этап 1: Результаты API поиска ======
        const stage1Score = data.original_score !== undefined ? data.original_score : data.score;
        stage1ScoreValue.textContent = stage1Score || '0';
        applyScoreStyle(stage1ScoreText, stage1Score || 0);

        // ====== Этап 2: Результаты верификации контента ======
        if (data.verified_url) {
            stage2Results.classList.remove('hidden');
            stage2ScoreValue.textContent = data.verified_score || '0';
            applyScoreStyle(stage2ScoreText, data.verified_score || 0);
            verifiedUrlLink.href = data.verified_url;
            verifiedUrlLink.textContent = data.verified_url;
            verificationError.classList.add('hidden');
        } else if (data.verification_error) {
            stage2Results.classList.add('hidden');
            verificationError.textContent = data.verification_error;
            verificationError.classList.remove('hidden');
        } else {
            stage2Results.classList.add('hidden');
            verificationError.classList.add('hidden');
        }

        // Инициализация видимости доменов для Этапа 1
        domainVisibility = {};
        const domains = getDomainsFromMatches(data.matches || []);
        domains.forEach(d => domainVisibility[d.url] = false); // По умолчанию выключено

        updateHighlightAllBtnText();
        renderMatches();
        updateLegendColor();
        applyAllHighlights(); // Начинаем с состоянием из domainVisibility (все false)

        // Переключаем вид
        textInput.classList.add('hidden');
        textHighlightView.classList.remove('hidden');
        checkButton.classList.add('hidden');
        resetButton.classList.remove('hidden');
    }

    function applyScoreStyle(element, score) {
        if (score >= 90) {
            element.className = 'text-2xl font-bold text-green-600 dark:text-green-500';
        } else if (score >= 50) {
            element.className = 'text-2xl font-bold text-yellow-600 dark:text-yellow-500';
        } else {
            element.className = 'text-2xl font-bold text-red-600 dark:text-red-500';
        }
    }

    function clearHighlights() {
        textHighlightView.innerHTML = escapeHtml(originalTextContent);
    }

    function getDomainsFromMatches(matches) {
        // Если сервер прислал готовый список ТОП-ов, используем его
        if (lastResultData && lastResultData.top_urls) {
            return lastResultData.top_urls.map(item => ({
                url: item.url,
                percent: Math.round(item.percent)
            }));
        }

        const domainMap = {};
        const totalChecked = lastResultData ? lastResultData.attempted_shingles : matches.length;

        matches.forEach(match => {
            match.urls.forEach(url => {
                if (!domainMap[url]) {
                    domainMap[url] = { url: url, count: 0 };
                }
                domainMap[url].count += 1;
            });
        });

        const score = parseFloat(stage1ScoreValue.textContent || '0');
        return Object.values(domainMap).map(d => ({
            url: d.url,
            percent: Math.round((d.count / (totalChecked || 1)) * 100)
        })).sort((a, b) => b.percent - a.percent);
    }

    function renderMatches() {
        matchesContainer.innerHTML = '';
        if (expandMatchesContainer) expandMatchesContainer.innerHTML = '';
        const allDomains = getDomainsFromMatches(currentMatches);

        if (allDomains.length === 0) {
            matchesContainer.innerHTML = '<p class="italic text-gray-500 py-4">Совпадений не найдено. Текст уникален!</p>';
            return;
        }

        // Ограничиваем список до 3 элементов, если он не развернут
        const visibleDomains = isResultsExpanded ? allDomains : allDomains.slice(0, 5);

        visibleDomains.forEach(domain => {
            const div = document.createElement('div');
            div.className = 'flex justify-between items-center py-2 group border-b border-gray-50 dark:border-gray-800 last:border-0';

            const isVisible = domainVisibility[domain.url];

            div.innerHTML = `
                <div class="flex items-center gap-3 overflow-hidden mr-4">
                    <a href="${domain.url}" target="_blank" class="text-blue-600 dark:text-blue-400 hover:underline truncate text-sm" title="${domain.url}">
                        ${domain.url}
                    </a>
                </div>
                <div class="flex items-center gap-4 flex-shrink-0">
                    <span class="text-emerald-600 font-bold text-sm w-12 text-right">${domain.percent}%</span>
                    <div class="flex items-center gap-2 text-gray-400">
                        <button class="hover:text-blue-600 toggle-visibility-btn" data-url="${domain.url}">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                ${isVisible ?
                    '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>' :
                    '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.04m5.882-5.916A8.923 8.923 0 0112 5c4.478 0 8.268 2.943 9.542 7a10.057 10.057 0 01-1.563 3.04l-7.218-7.218z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3l18 18"></path>'}
                            </svg>
                        </button>
                        <svg class="w-5 h-5 cursor-move" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l4-4 4 4m0 6l-4 4-4-4"></path>
                        </svg>
                    </div>
                </div>
            `;

            div.querySelector('.toggle-visibility-btn').onclick = () => {
                domainVisibility[domain.url] = !domainVisibility[domain.url];

                // Если включили домен, активируем этап 1 и выключаем этап 2
                if (domainVisibility[domain.url]) {
                    stage1HighlightActive = true;
                    stage2HighlightActive = false;
                    updateStage2UI();
                    updateStage1UI();
                }

                updateHighlightAllBtnText();
                renderMatches();
                updateLegendColor();
                applyAllHighlights();
            };

            matchesContainer.appendChild(div);
        });

        // Добавляем кнопку "Развернуть / Свернуть", если доменов больше 5
        if (allDomains.length > 5 && expandMatchesContainer) {
            const toggleWrapper = document.createElement('div');
            toggleWrapper.className = 'text-center'; // Убрали pt-2 т.к. теперь в шапке

            const toggleBtn = document.createElement('button');
            toggleBtn.className = 'text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium focus:outline-none flex items-center justify-center gap-1 mx-auto py-1 px-3 bg-gray-100 dark:bg-gray-700 rounded-full transition-colors hover:bg-gray-200 dark:hover:bg-gray-600';

            if (isResultsExpanded) {
                toggleBtn.innerHTML = `
                    <span>Свернуть список</span>
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"></path></svg>
                `;
            } else {
                toggleBtn.innerHTML = `
                    <span>Развернуть (еще ${allDomains.length - 5})</span>
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                `;
            }

            toggleBtn.onclick = () => {
                isResultsExpanded = !isResultsExpanded;
                renderMatches();
            };

            toggleWrapper.appendChild(toggleBtn);
            expandMatchesContainer.appendChild(toggleWrapper);
        }
    }





    function updateHistoryRow(taskId, data, percent = null) {
        const row = document.getElementById(`task-row-${taskId}`);
        if (!row) return;

        const scoreCell = row.cells[1];
        const statusCell = row.cells[2];

        if (data.status === 'completed') {
            const result = data.result;
            const score = result.stage2_result ? result.stage2_result.score : result.score;

            let colorClass = 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
            if (score >= 80) colorClass = 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
            else if (score >= 50) colorClass = 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';

            scoreCell.innerHTML = `<span class="px-2 py-1 rounded text-xs font-bold ${colorClass}">${score}%</span>`;
            statusCell.innerHTML = `<span class="px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">Выполнено</span>`;
        } else if (data.status === 'error') {
            statusCell.innerHTML = `<span class="px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">Ошибка</span>`;
        } else if (data.status === 'running' && percent !== null) {
            statusCell.innerHTML = `<span class="px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">В работе (${percent}%)</span>`;
        }
    }

    function showError(msg) {
        errorContainer.textContent = msg;
        errorContainer.classList.remove('hidden');
        window.scrollTo({ top: errorContainer.offsetTop - 100, behavior: 'smooth' });
    }

    // --- Глобальные функции для работы с историей ---
    window.loadTaskResult = function (taskId) {
        const loadingMessage = document.getElementById('loadingMessage');
        const loadingProgressBlock = document.getElementById('loadingProgressBlock');

        if (loadingMessage) loadingMessage.textContent = 'Загрузка результата...';
        if (loadingProgressBlock) loadingProgressBlock.classList.add('hidden');

        loadingOverlay.classList.remove('hidden');
        fetch(`/uniqueness/status/${taskId}`)
            .then(res => res.json())
            .then(data => {
                loadingOverlay.classList.add('hidden');
                if (data.status === 'completed') {
                    if (data.result) {
                        // Важно: восстанавливаем текст для корректной подсветки
                        if (data.source_text) {
                            textInput.value = data.source_text;
                            originalTextContent = data.source_text;
                            charCount.textContent = data.source_text.length;
                        }

                        currentMatches = data.result.matches || [];
                        displayResults(data.result);
                        window.scrollTo({ top: uniquenessResults.offsetTop - 50, behavior: 'smooth' });
                    } else {
                        showError('Результаты задачи отсутствуют в базе.');
                    }
                } else if (data.status === 'running') {
                    if (loadingMessage) loadingMessage.textContent = 'Проверка уникальности...';
                    if (loadingProgressBlock) loadingProgressBlock.classList.remove('hidden');
                    pollTaskStatus(taskId);
                } else if (data.status === 'error') {
                    showError(data.error || 'Ошибка в задаче.');
                }
            })
            .catch(err => {
                loadingOverlay.classList.add('hidden');
                showError('Ошибка загрузки результата: ' + err.message);
            });
    };

    window.deleteTask = function (taskId) {
        if (!confirm('Вы уверены, что хотите удалить эту проверку из истории?')) return;

        fetch(`/uniqueness/delete/${taskId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
            }
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const row = document.getElementById(`task-row-${taskId}`);
                    if (row) row.remove();

                    // Если история пуста, можно скрыть блок (опционально)
                    const tbody = document.querySelector('#uniquenessHistory tbody');
                    if (tbody && tbody.children.length === 0) {
                        document.getElementById('uniquenessHistory').remove();
                    }
                } else {
                    alert('Ошибка: ' + data.error);
                }
            })
            .catch(err => alert('Ошибка при удалении: ' + err.message));
    };

    // Авто-поллинг для задач, которые "В работе" при загрузке страницы
    const runningTasks = document.querySelectorAll('tr[id^="task-row-"]');
    runningTasks.forEach(row => {
        if (row.textContent.includes('В работе')) {
            const taskId = row.id.replace('task-row-', '');
            pollTaskStatus(taskId);
        }
    });
});
