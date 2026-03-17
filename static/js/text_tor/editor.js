document.addEventListener('DOMContentLoaded', function() {
    const tableBody = document.querySelector('tbody');
    const storageKey = 'torResultsData';
    const hybridStorageKey = 'hybridTorData';
    const urlParams = new URLSearchParams(window.location.search);

    // Эта часть выполняется только когда данные приходят с сервера
    if (urlParams.has('result_ids')) {
        const initialDataElement = document.getElementById('initial-data');
        if (initialDataElement && initialDataElement.textContent) {
            const newResults = JSON.parse(initialDataElement.textContent);
            let storedResults = JSON.parse(localStorage.getItem(storageKey)) || [];
            const storedIds = new Set(storedResults.map(item => String(item.id)));

            newResults.forEach(newItem => {
                if (!storedIds.has(String(newItem.id))) {
                    storedResults.push(newItem);
                    console.log(`Добавлен новый результат с ID: ${newItem.id} в localStorage`);
                }
            });

            localStorage.setItem(storageKey, JSON.stringify(storedResults));

            // Очищаем URL от result_ids, чтобы при перезагрузке сработал loader
            window.history.replaceState({}, document.title, window.location.pathname);
            console.log('URL очищен. Перезагрузка для отображения данных из localStorage...');
            // Перезагружаем страницу, чтобы loader отобразил объединенные данные
            window.location.reload();
        }
    }

    // Делегирование событий для отслеживания изменений в редактируемых ячейках
    tableBody.addEventListener('input', function(e) {
        if (e.target && e.target.hasAttribute('contenteditable')) {
            const cell = e.target;
            const row = cell.closest('tr');
            const url = row.getAttribute('data-result-url');
            const field = cell.getAttribute('data-field');
            let newValue;

            if (field === 'headings') {
                const headings = [];
                // Разбираем HTML и извлекаем текст заголовков
                const lines = cell.innerText.split('\n');
                lines.forEach(line => {
                    const cleanedLine = line.trim();
                    if (cleanedLine) {
                        const match = cleanedLine.match(/H(\d+): (.*)/);
                        if (match) {
                            headings.push({ level: parseInt(match[1], 10), text: match[2].trim() });
                        } else {
                            // Если строка не соответствует формату, считаем ее обычным текстом с уровнем заголовка по умолчанию (например, 2)
                            headings.push({ level: 2, text: cleanedLine });
                        }
                    }
                });
                newValue = JSON.stringify(headings);

            } else if (field === 'lsi_words') {
                // Используем innerText, чтобы получить чистый текст без HTML-тегов,
                // а затем разделяем его по символам новой строки.
                const words = cell.innerText.split('\n')
                    .map(word => word.trim()) // Убираем лишние пробелы
                    .filter(word => word.length > 0); // Удаляем пустые строки
                newValue = JSON.stringify(words);

            } else {
                newValue = cell.innerText; // Для остальных полей используем innerText
            }

            let storedData = JSON.parse(localStorage.getItem(storageKey)) || [];
            const itemIndex = storedData.findIndex(item => item.url === url);

            if (itemIndex > -1) {
                if (field === 'headings') {
                    // Сохраняем сгенерированные заголовки в отдельный ключ
                    let hybridData = JSON.parse(localStorage.getItem(hybridStorageKey)) || {};
                    hybridData.generatedHeadings = JSON.parse(newValue);
                    localStorage.setItem(hybridStorageKey, JSON.stringify(hybridData));
                    console.log(`Сгенерированные заголовки сохранены в localStorage (hybridTorData)`);
                }

                storedData[itemIndex][field] = newValue;
                localStorage.setItem(storageKey, JSON.stringify(storedData));
                console.log(`Обновлено поле "${field}" для URL: ${url}`);
            }
        }
    });

    // Обработчик для сохранения сгенерированной структуры заголовков
    const headingsResultEl = document.getElementById('headings-generation-result');
    if (headingsResultEl) {
        headingsResultEl.addEventListener('input', function(e) {
            const cell = e.target;
            const headings = [];
            const lines = cell.innerText.split('\n');
            lines.forEach(line => {
                const cleanedLine = line.trim();
                if (cleanedLine) {
                    const match = cleanedLine.match(/H(\d+): (.*)/);
                    if (match) {
                        headings.push({ level: parseInt(match[1], 10), text: match[2].trim() });
                    } else {
                        headings.push({ level: 2, text: cleanedLine });
                    }
                }
            });
            
            let hybridData = JSON.parse(localStorage.getItem(hybridStorageKey)) || {};
            hybridData.generatedHeadings = headings;
            localStorage.setItem(hybridStorageKey, JSON.stringify(hybridData));
            console.log(`Сгенерированные заголовки сохранены в localStorage (hybridTorData)`);
        });
    }

    // Обработчик для сохранения сгенерированных LSI-слов
    const lsiResultEl = document.getElementById('lsi-generation-result');
    if (lsiResultEl) {
        lsiResultEl.addEventListener('input', function(e) {
            const cell = e.target;
            const lsiWords = cell.innerText.split('\n')
                .map(word => word.trim())
                .filter(word => word.length > 0);
            
            let hybridData = JSON.parse(localStorage.getItem(hybridStorageKey)) || {};
            hybridData.generatedLsi = lsiWords;
            localStorage.setItem(hybridStorageKey, JSON.stringify(hybridData));
            console.log(`Сгенерированные LSI-слова сохранены в localStorage (hybridTorData)`);
        });
    }
});