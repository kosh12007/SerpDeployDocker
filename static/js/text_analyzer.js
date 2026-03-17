document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('textAnalyzerForm');
    const inputContainer = document.getElementById('inputContainer');
    const textInput = document.getElementById('textInput');
    const textHighlightView = document.getElementById('textHighlightView');
    const analyzeButton = document.getElementById('analyzeButton');
    const resetButton = document.getElementById('resetButton');
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsContent = document.getElementById('resultsContent');
    const activeHighlightLabel = document.getElementById('activeHighlightLabel');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const errorContainer = document.getElementById('errorContainer');

    // Элементы таблиц частотности
    const freqTable1 = document.getElementById('freqTable1');
    const freqTable2 = document.getElementById('freqTable2');
    const freqTable3 = document.getElementById('freqTable3');
    const freqTableStop = document.getElementById('freqTableStop');

    let currentAnalysisData = null;
    let activeHighlight = null;

    form.addEventListener('submit', function (event) {
        event.preventDefault();

        // Скрываем результаты и ошибки
        resultsContainer.classList.add('hidden');
        errorContainer.classList.add('hidden');
        errorContainer.textContent = '';
        textHighlightView.classList.add('hidden');
        textHighlightView.innerHTML = '';
        activeHighlightLabel.textContent = '';

        // Показываем спиннер
        loadingSpinner.classList.remove('hidden');
        analyzeButton.disabled = true;

        const inputType = document.querySelector('input[name="inputType"]:checked').value;
        const textValue = textInput.value.trim();

        if (!textValue) {
            showError('Пожалуйста, введите текст или URL.');
            return;
        }

        fetch('/analyze-text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
            },
            body: JSON.stringify({
                text_input: textValue,
                input_type: inputType
            })
        })
            .then(response => response.json())
            .then(data => {
                loadingSpinner.classList.add('hidden');
                analyzeButton.disabled = false;

                if (data.success) {
                    currentAnalysisData = data.data;
                    displayResults(data.data);
                    switchToResultView(data.data.text_content);
                } else {
                    showError(data.error || 'Произошла ошибка при анализе текста.');
                }
            })
            .catch(error => {
                loadingSpinner.classList.add('hidden');
                analyzeButton.disabled = false;
                showError('Произошла ошибка при отправке запроса: ' + error.message);
            });
    });

    resetButton.addEventListener('click', function () {
        // Сброс к начальному состоянию
        inputContainer.classList.remove('hidden');
        textHighlightView.classList.add('hidden');
        textHighlightView.innerHTML = '';
        resultsContainer.classList.add('hidden');
        resetButton.classList.add('hidden');
        analyzeButton.classList.remove('hidden');
        textInput.value = '';
        currentAnalysisData = null;
        activeHighlight = null;
    });

    function switchToResultView(content) {
        inputContainer.classList.add('hidden');
        textHighlightView.classList.remove('hidden');
        // Используем textContent для безопасности, но нам нужно форматирование
        // Если контент приходит с \n, заменяем их на <br> или оборачиваем в <p>

        // Лучший способ сохранить структуру - разбить по \n и обернуть в p/div
        const safeContent = content.split('\n').filter(line => line.trim() !== '').map(line => `<p class="mb-2">${escapeHtml(line)}</p>`).join('');
        textHighlightView.innerHTML = safeContent;

        resetButton.classList.remove('hidden');
        analyzeButton.classList.add('hidden');
    }

    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, function (m) { return map[m]; });
    }

    // Глобальная функция для вызова из HTML кнопок
    window.toggleHighlight = function (metricType) {
        if (!currentAnalysisData) return;

        // Если уже активно - сбрасываем
        if (activeHighlight === metricType) {
            // Сброс
            const originalText = currentAnalysisData.text_content;
            const safeContent = originalText.split('\n').filter(line => line.trim() !== '').map(line => `<p class="mb-2">${escapeHtml(line)}</p>`).join('');
            textHighlightView.innerHTML = safeContent;
            activeHighlight = null;
            activeHighlightLabel.textContent = '';
            // Снимаем выделение с кнопки (визуально можно добавить позже)
            return;
        }

        activeHighlight = metricType;

        let wordsToHighlight = {}; // word -> intensity/count
        let colorClassBase = '';
        let label = '';

        if (metricType === 'water') {
            // Для воды подсвечиваем стоп-слова
            // Создадим словарь из списка для быстрого поиска
            currentAnalysisData.water_words.forEach(word => {
                wordsToHighlight[word.toLowerCase()] = 1; // Равномерная подсветка или можно считать частоту
            });
            colorClassBase = 'bg-blue-200 dark:bg-blue-900';
            label = 'Подсвечено: Водность';
        } else if (metricType === 'spam') {
            // Заспамленность - повторяющиеся слова (те, у которых freq > 1) среди значимых
            for (const [word, count] of Object.entries(currentAnalysisData.content_word_frequency)) {
                if (count > 1) {
                    wordsToHighlight[word.toLowerCase()] = count;
                }
            }
            colorClassBase = 'bg-red-200 dark:bg-red-900';
            label = 'Подсвечено: Заспамленность';
        } else if (metricType === 'nausea') {
            // Тошнота - самые частые значимые слова
            const sorted = Object.entries(currentAnalysisData.content_word_frequency).sort((a, b) => b[1] - a[1]);
            const maxFreq = sorted[0] ? sorted[0][1] : 0;
            // Подсветим топ 5
            sorted.slice(0, 5).forEach(([word, count]) => {
                wordsToHighlight[word.toLowerCase()] = count;
            });
            colorClassBase = 'bg-yellow-200 dark:bg-yellow-900';
            label = 'Подсвечено: Тошнота (топ-5 значимых слов)';
        }

        activeHighlightLabel.textContent = label;
        activeHighlightLabel.className = 'text-sm font-semibold ' + (
            metricType === 'water' ? 'text-blue-600' :
                metricType === 'spam' ? 'text-red-600' : 'text-yellow-600'
        );

        // Применяем подсветку
        applyHighlight(wordsToHighlight, colorClassBase, metricType);
    };

    function applyHighlight(targetWords, colorClassBase, metricType) {
        const originalText = currentAnalysisData.text_content;

        // Разбиваем на абзацы
        const paragraphs = originalText.split('\n').filter(line => line.trim() !== '');

        let highlightedHtml = '';

        // Определяем макс частоту для градации (если применимо)
        let maxCount = 0;
        if (metricType !== 'water') {
            maxCount = Math.max(...Object.values(targetWords), 1);
        }

        paragraphs.forEach(paragraph => {
            // Разбиваем абзац на токены, сохраняя разделители, чтобы потом собрать обратно
            // Используем regex с capture group для разделителей
            const parts = paragraph.split(/([^\wа-яёА-ЯЁ0-9]+)/u);

            const pContent = parts.map(part => {
                const lowerPart = part.toLowerCase();
                if (targetWords.hasOwnProperty(lowerPart)) {
                    const count = targetWords[lowerPart];

                    // Вычисляем opacity для градации (от 0.3 до 1)
                    let opacity = 1;
                    if (metricType !== 'water' && maxCount > 1) {
                        opacity = 0.3 + (0.7 * (count / maxCount));
                    }

                    // Стиль
                    let style = `background-color: ${getColorCode(metricType, opacity)}; padding: 0 2px; border-radius: 2px;`;
                    return `<span style="${style}" title="Частота: ${count}">${escapeHtml(part)}</span>`;
                }
                return escapeHtml(part);
            }).join('');

            highlightedHtml += `<p class="mb-2">${pContent}</p>`;
        });

        textHighlightView.innerHTML = highlightedHtml;
    }

    function getColorCode(type, opacity) {
        // Hex цвета с альфа-каналом не всегда удобны, используем rgba
        if (type === 'water') return `rgba(59, 130, 246, ${opacity || 0.5})`; // Blue
        if (type === 'spam') return `rgba(239, 68, 68, ${opacity})`; // Red
        if (type === 'nausea') return `rgba(234, 179, 8, ${opacity})`; // Yellow/Orange
        return 'transparent';
    }

    function displayResults(data) {
        function getColorClass(value, metricType) {
            if (metricType === 'classic_nausea') {
                if (value <= 3) return 'text-green-600 dark:text-green-400';
                if (value <= 7) return 'text-yellow-600 dark:text-yellow-400';
                return 'text-red-600 dark:text-red-400';
            } else if (metricType === 'academic_nausea') {
                if (value <= 4) return 'text-green-600 dark:text-green-400';
                if (value <= 7) return 'text-yellow-600 dark:text-yellow-400';
                return 'text-red-600 dark:text-red-400';
            } else if (metricType === 'spam_score') {
                if (value <= 30) return 'text-green-600 dark:text-green-400';
                if (value <= 60) return 'text-yellow-600 dark:text-yellow-400';
                return 'text-red-600 dark:text-red-400';
            } else if (metricType === 'water_percentage') {
                if (value <= 15) return 'text-green-600 dark:text-green-400';
                if (value <= 30) return 'text-yellow-600 dark:text-yellow-400';
                return 'text-red-600 dark:text-red-400';
            }
            return '';
        }

        let resultHtml = '';
        resultHtml += '<div class="mb-4">';
        // Тип ввода уже не так важен в карточках, он виден по полю
        resultHtml += '</div>';

        resultHtml += '<div class="grid grid-cols-1 md:grid-cols-2 gap-4">';

        // Статистика символов (без кнопок подсветки)
        resultHtml += `
            <div class="p-4 bg-gray-100 dark:bg-gray-700 rounded-lg">
                <h4 class="font-medium mb-2">Символов (с пробелами / без)</h4>
                <p class="text-2xl font-bold gap-2">
                    ${data.chars_with_spaces} <span class="text-sm text-gray-500">/</span> ${data.chars_without_spaces}
                </p>
                <div class="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-sm text-gray-500">
                    <p>Всего слов: <span class="font-semibold text-gray-700 dark:text-gray-300">${data.word_count}</span></p>
                    <p>Уникальных: <span class="font-semibold text-gray-700 dark:text-gray-300">${data.unique_word_count}</span></p>
                </div>
            </div>
        `;

        // Водность
        resultHtml += `
            <div class="p-4 bg-gray-100 dark:bg-gray-700 rounded-lg relative group">
                <div class="flex justify-between items-start">
                    <h4 class="font-medium mb-2">Водность</h4>
                    <button onclick="toggleHighlight('water')" class="text-xs bg-blue-100 hover:bg-blue-200 text-blue-800 px-2 py-1 rounded transition-colors">Подсветить</button>
                </div>
                <p class="text-2xl font-bold ${getColorClass(data.water_percentage, 'water_percentage')}">${data.water_percentage}%</p>
                <div class="mt-2 text-sm">
                    <p class="${data.water_percentage <= 15 ? 'text-green-600 dark:text-green-400' : ''}${data.water_percentage > 15 && data.water_percentage <= 30 ? 'text-yellow-600 dark:text-yellow-400' : ''}${data.water_percentage > 30 ? 'text-red-600 dark:text-red-400' : ''}">
                         Рекомендуемая градация для SEO:
                    </p>
                    <ul class="list-disc pl-5 mt-1 text-xs">
                        <li class="text-green-600 dark:text-green-400">Оптимально: ≤ 15%</li>
                        <li class="text-yellow-600 dark:text-yellow-400">Умеренно: 15-30%</li>
                        <li class="text-red-600 dark:text-red-400">Высоко: > 30%</li>
                    </ul>
                </div>
            </div>
        `;

        // Тошнота
        resultHtml += `
             <div class="p-4 bg-gray-100 dark:bg-gray-700 rounded-lg relative group">
                <div class="flex justify-between items-start">
                    <h4 class="font-medium mb-2">Тошнота</h4>
                    <button onclick="toggleHighlight('nausea')" class="text-xs bg-yellow-100 hover:bg-yellow-200 text-yellow-800 px-2 py-1 rounded transition-colors">Подсветить</button>
                </div>
                <div class="flex flex-col gap-2">
                    <div class="flex items-end gap-2">
                        <span class="text-2xl font-bold ${getColorClass(data.classic_nausea, 'classic_nausea')}">${data.classic_nausea}</span>
                        <span class="text-xs text-gray-400 mb-1">Классическая</span>
                    </div>
                    <div class="flex items-end gap-2">
                        <span class="text-2xl font-bold ${getColorClass(data.academic_nausea, 'academic_nausea')}">${data.academic_nausea}%</span>
                        <span class="text-xs text-gray-400 mb-1">Академическая</span>
                    </div>
                </div>
                <div class="mt-2 text-sm">
                    <p class="${data.academic_nausea <= 4 ? 'text-green-600 dark:text-green-400' : ''}${data.academic_nausea > 4 && data.academic_nausea <= 7 ? 'text-yellow-600 dark:text-yellow-400' : ''}${data.academic_nausea > 7 ? 'text-red-600 dark:text-red-400' : ''}">
                        Рекомендуемые SEO-нормы:
                    </p>
                    <ul class="list-disc pl-5 mt-1 text-xs space-y-1">
                        <li class="flex justify-between">
                            <span>Классическая:</span>
                            <span class="font-mono text-indigo-600 dark:text-indigo-400">3 – 5 (до 7)</span>
                        </li>
                        <li class="flex justify-between">
                            <span>Академическая:</span>
                            <span class="font-mono text-indigo-600 dark:text-indigo-400">4% – 6% (до 7%)</span>
                        </li>
                    </ul>
                </div>
            </div>
        `;

        // Заспамленность
        resultHtml += `
             <div class="p-4 bg-gray-100 dark:bg-gray-700 rounded-lg relative group">
                <div class="flex justify-between items-start">
                    <h4 class="font-medium mb-2">Заспамленность</h4>
                    <button onclick="toggleHighlight('spam')" class="text-xs bg-red-100 hover:bg-red-200 text-red-800 px-2 py-1 rounded transition-colors">Подсветить</button>
                </div>
                <p class="text-2xl font-bold ${getColorClass(data.spam_score, 'spam_score')}">${data.spam_score}%</p>
                 <div class="mt-2 text-sm">
                    <p class="${data.spam_score <= 30 ? 'text-green-600 dark:text-green-400' : ''}${data.spam_score > 30 && data.spam_score <= 60 ? 'text-yellow-600 dark:text-yellow-400' : ''}${data.spam_score > 60 ? 'text-red-600 dark:text-red-400' : ''}">
                        Рекомендуемая градация для SEO:
                    </p>
                    <ul class="list-disc pl-5 mt-1 text-xs">
                        <li class="text-green-600 dark:text-green-400">Оптимально: ≤ 30%</li>
                        <li class="text-yellow-600 dark:text-yellow-400">Умеренно: 30-60%</li>
                        <li class="text-red-600 dark:text-red-400">Высоко: > 60%</li>
                    </ul>
                </div>
            </div>
        `;

        resultHtml += '</div>';
        resultsContent.innerHTML = resultHtml;
        resultsContainer.classList.remove('hidden');

        // Рендеринг таблиц частотности
        renderFreqTables(data.top_ngrams);

        // Показываем блок экспорта
        const resultsActions = document.getElementById('results-actions');
        if (resultsActions) {
            resultsActions.classList.remove('hidden');
        }
    }

    // --- Функции экспорта и копирования ---

    // Копирование в буфер
    const copyBtn = document.getElementById('copy-results-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', function () {
            if (!currentAnalysisData) return;

            const data = currentAnalysisData;
            let text = `СВОДКА АНАЛИЗА ТЕКСТА\n`;
            text += `========================\n`;
            text += `Символов (с пробелами): ${data.chars_with_spaces}\n`;
            text += `Символов (без пробелов): ${data.chars_without_spaces}\n`;
            text += `Всего слов: ${data.word_count}\n`;
            text += `Уникальных слов: ${data.unique_word_count}\n`;
            text += `Водность: ${data.water_percentage}%\n`;
            text += `Тошнота (Классическая): ${data.classic_nausea}\n`;
            text += `Тошнота (Академическая): ${data.academic_nausea}%\n`;
            text += `Заспамленность: ${data.spam_score}%\n\n`;

            text += `ТОП СЛОВА (1-граммы):\n`;
            data.top_ngrams['1_word'].forEach(([word, count]) => {
                text += `- ${word}: ${count}\n`;
            });

            text += `\nФРАЗЫ (2 слова):\n`;
            data.top_ngrams['2_words'].forEach(([phrase, count]) => {
                text += `- ${phrase}: ${count}\n`;
            });

            text += `\nФРАЗЫ (3 слова):\n`;
            data.top_ngrams['3_words'].forEach(([phrase, count]) => {
                text += `- ${phrase}: ${count}\n`;
            });

            text += `\nСТОП-СЛОВА:\n`;
            data.top_ngrams['stop_words'].forEach(([word, count]) => {
                text += `- ${word}: ${count}\n`;
            });

            navigator.clipboard.writeText(text).then(() => {
                alert('Результаты скопированы в буфер обмена!');
            }).catch(err => {
                console.error('Ошибка копирования:', err);
                alert('Не удалось скопировать результаты.');
            });
        });
    }

    // Скачивание файлов
    function downloadResults(format, encoding = 'utf-8') {
        if (!currentAnalysisData) {
            alert('Нет данных для скачивания.');
            return;
        }

        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/download-text-results?format=${format}&encoding=${encoding}`;

        const hiddenField = document.createElement('input');
        hiddenField.type = 'hidden';
        hiddenField.name = 'results_data';
        hiddenField.value = JSON.stringify(currentAnalysisData);
        form.appendChild(hiddenField);

        const csrfToken = document.querySelector('input[name="csrf_token"]').value;
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrf_token';
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);

        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    }

    const xlsxBtn = document.getElementById('download-xlsx-btn');
    if (xlsxBtn) xlsxBtn.addEventListener('click', () => downloadResults('xlsx'));

    const csvUtf8Btn = document.getElementById('download-csv-utf8-btn');
    if (csvUtf8Btn) csvUtf8Btn.addEventListener('click', () => downloadResults('csv', 'utf-8'));

    const csvWin1251Btn = document.getElementById('download-csv-win1251-btn');
    if (csvWin1251Btn) csvWin1251Btn.addEventListener('click', () => downloadResults('csv', 'windows-1251'));

    const txtBtn = document.getElementById('download-txt-btn');
    if (txtBtn) txtBtn.addEventListener('click', () => downloadResults('txt'));


    function renderFreqTables(ngrams) {
        function createTable(items) {
            if (!items || items.length === 0) return '<p class="text-xs text-gray-400 italic">Нет данных</p>';

            let html = '<table class="w-full text-left border-collapse">';
            html += '<thead><tr><th class="border-b dark:border-gray-700 p-1 text-xs text-gray-500 uppercase tracking-tighter">Слово/Фраза</th><th class="border-b dark:border-gray-700 p-1 text-xs text-gray-500 text-right uppercase tracking-tighter">Кол-во</th></tr></thead>';
            html += '<tbody>';
            items.forEach(([word, count]) => {
                html += `<tr><td class="border-b border-gray-100 dark:border-gray-700 p-1 truncate max-w-[150px] text-[13px]" title="${word}">${word}</td><td class="border-b border-gray-100 dark:border-gray-700 p-1 text-right font-mono text-xs">${count}</td></tr>`;
            });
            html += '</tbody></table>';
            return html;
        }

        freqTable1.innerHTML = createTable(ngrams['1_word']);
        freqTable2.innerHTML = createTable(ngrams['2_words']);
        freqTable3.innerHTML = createTable(ngrams['3_words']);
        if (freqTableStop) {
            freqTableStop.innerHTML = createTable(ngrams['stop_words']);
        }
    }

    function showError(message) {
        errorContainer.textContent = message;
        errorContainer.classList.remove('hidden');
        loadingSpinner.classList.add('hidden');
    }

    const inputTypeRadios = document.querySelectorAll('input[name="inputType"]');
    inputTypeRadios.forEach(radio => {
        radio.addEventListener('change', function () {
            if (this.value === 'url') {
                textInput.placeholder = 'Введите URL веб-страницы...';
            } else {
                textInput.placeholder = 'Введите ваш текст здесь...';
            }
        });
    });
});