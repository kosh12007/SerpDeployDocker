document.addEventListener('DOMContentLoaded', function () {
    const generateBtn = document.getElementById('generate-lsi-btn');
    const getLastTaskBtn = document.getElementById('get-last-task-lsi-btn');
    const statusDiv = document.getElementById('lsi-generation-status');
    const resultDiv = document.getElementById('lsi-generation-result');
    resultDiv.style.textTransform = 'none'; // Сбрасываем трансформацию текста
    const hybridStorageKey = 'hybridTorData';

    let pollingInterval; // Интервал для опроса статуса

    // --- Helper Functions ---

    function parseLsi(text) {
        if (!text) return [];
        return text.split('\n').map(line => line.trim()).filter(line => line);
    }

    function displayLsi(lsiArray) {
        if (lsiArray && lsiArray.length > 0) {
            resultDiv.innerHTML = lsiArray.join('<br>');
        } else {
            resultDiv.innerHTML = '';
        }
    }

    function loadLsiFromStorage() {
        const hybridData = JSON.parse(localStorage.getItem(hybridStorageKey)) || {};
        if (hybridData.generatedLsi) {
            displayLsi(hybridData.generatedLsi);
        }
    }

    // --- Event Listeners ---

    generateBtn.addEventListener('click', async () => {
        try {
            statusDiv.textContent = 'Подготовка данных...';
            const torResultsData = JSON.parse(localStorage.getItem('torResultsData')) || [];
            const hybridTorData = JSON.parse(localStorage.getItem('hybridTorData')) || {};

            if (torResultsData.length === 0) {
                statusDiv.textContent = 'Ошибка: Нет данных для анализа (torResultsData).';
                return;
            }

            let allLsiWords = [];
            torResultsData.forEach(item => {
                if (item.lsi_words) {
                    try {
                        const lsi = JSON.parse(item.lsi_words);
                        allLsiWords.push(...lsi);
                    } catch (e) {
                        console.error('Ошибка парсинга LSI:', e);
                    }
                }
            });

            if (allLsiWords.length === 0) {
                statusDiv.textContent = 'Ошибка: Не найдено ни одного LSI-слова для анализа.';
                return;
            }

            // Удаляем дубликаты
            allLsiWords = [...new Set(allLsiWords)];

            const system_prompt = `Твоя задача — проанализировать предоставленный список LSI-ключей (Latent Semantic Indexing), собранных с разных сайтов. На основе этого списка ты должен составить единый, очищенный и структурированный перечень LSI-слов, который будет использоваться для написания SEO-оптимизированной статьи.

Инструкции:
1.  **Удали дубликаты:** Оставь только уникальные слова и фразы.
2.  **Сгруппируй по смыслу:** Объедини близкие по значению или тематике слова в логические группы.
3.  **Приоритезируй:** Расположи слова и фразы в порядке убывания их важности для раскрытия основной темы. Наиболее значимые — вверху списка.
4.  **Очисти от мусора:** Исключи общие слова, стоп-слова и фразы, не несущие смысловой нагрузки (например, "цена", "купить", "отзывы", если они не являются ядром семантики).
5.  **Представь результат:** Выдай итоговый список в виде перечня слов, где каждое слово или фраза находится на новой строке. Без заголовков, нумерации или каких-либо пояснений.

Пример исходных данных:
"ремонт квартир, стоимость ремонта, ремонт под ключ, дизайн интерьера, смета на ремонт, отделочные работы, ремонт в новостройке, цена ремонта квартиры"

Пример идеального результата:
ремонт квартир под ключ
дизайн интерьера
отделочные работы
смета на ремонт
ремонт в новостройке
стоимость ремонта`;
            const user_message = `Список LSI-слов: ${allLsiWords.join(', ')}`;

            statusDiv.textContent = 'Отправка запроса к AI...';

            const formData = new FormData();
            formData.append('system_prompt', system_prompt);
            formData.append('user_message', user_message);

            const response = await fetch('/ask-ai', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Ошибка сети: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.status === 'success' && data.task_id) {
                const taskId = data.task_id;
                const hybridData = JSON.parse(localStorage.getItem(hybridStorageKey)) || {};
                hybridData.lsiGenerationTaskId = taskId;
                localStorage.setItem(hybridStorageKey, JSON.stringify(hybridData));
                statusDiv.textContent = `Задача ${taskId} создана. Ожидание результата...`;
                Toastify({
                    text: data.message || "Задача на генерацию LSI создана",
                    duration: 3000,
                    style: {
                        background: "#4CAF50"
                    },
                }).showToast();
                startPolling(taskId); // Начинаем опрос
            } else {
                statusDiv.textContent = `Ошибка: ${data.message || 'Не удалось получить ID задачи.'}`;
            }
        } catch (error) {
            statusDiv.textContent = `Критическая ошибка: ${error.message}`;
            console.error(error);
        }
    });

    getLastTaskBtn.addEventListener('click', async () => {
        const hybridData = JSON.parse(localStorage.getItem(hybridStorageKey)) || {};
        const taskId = hybridData.lsiGenerationTaskId;
        if (!taskId) {
            statusDiv.textContent = 'ID последней задачи не найден.';
            return;
        }
        startPolling(taskId);
    });


    function getStatusClass(status) {
        switch (status) {
            case 'completed':
                return 'bg-green-200 text-green-800';
            case 'running':
                return 'bg-blue-200 text-blue-800';
            case 'pending':
                return 'bg-yellow-200 text-yellow-800';
            default:
                return 'bg-red-200 text-red-800';
        }
    }

    function getStatusText(status) {
        switch (status) {
            case 'completed':
                return 'Выполнено';
            case 'running':
                return 'В работе';
            case 'pending':
                return 'В очереди';
            default:
                return 'Ошибка';
        }
    }

    function updateTaskStatusUI(status, taskId) {
        const statusSpan = document.createElement('span');
        statusSpan.className = `session-status ${getStatusClass(status)}`;
        statusSpan.textContent = getStatusText(status);

        statusDiv.innerHTML = `Статус задачи ${taskId}: `;
        statusDiv.appendChild(statusSpan);
        statusDiv.classList.remove('hidden');
    }

    async function checkTaskStatus(taskId) {
        try {
            const response = await fetch(`/text-tor/task-status/${taskId}`);
            if (response.status === 404) {
                // Если задача не найдена, очищаем localStorage и сообщаем
                let hybridTorData = JSON.parse(localStorage.getItem(hybridStorageKey)) || {};
                delete hybridTorData.lsiGenerationTaskId;
                delete hybridTorData.generatedLsi;
                localStorage.setItem(hybridStorageKey, JSON.stringify(hybridTorData));
                resultDiv.innerHTML = '';
                statusDiv.textContent = 'Последняя задача не найдена. Данные очищены.';
                return 'not_found';
            }

            if (!response.ok) {
                throw new Error('Не удалось получить статус задачи.');
            }
            const data = await response.json();

            updateTaskStatusUI(data.status, taskId);

            if (data.status === 'completed') {
                setTimeout(() => {
                    statusDiv.classList.add('hidden');
                }, 2000);

                resultDiv.innerHTML = data.ai_response ? data.ai_response.replace(/\n/g, '<br>') : 'Результат пуст.';
                resultDiv.classList.remove('hidden');

                let hybridTorData = JSON.parse(localStorage.getItem('hybridTorData')) || {};
                const lsiArray = parseLsi(data.ai_response);
                hybridTorData.generatedLsi = lsiArray;
                localStorage.setItem('hybridTorData', JSON.stringify(hybridTorData));
                displayLsi(lsiArray); // Отображаем результат

                return 'completed';

            } else if (data.status === 'error') {
                statusDiv.textContent = `Ошибка выполнения задачи ${taskId}: ${data.message}`;
                return 'error';
            }
            return data.status; // 'running' or 'pending'
        } catch (error) {
            statusDiv.textContent = `Ошибка опроса статуса: ${error.message}`;
            console.error(error);
            return 'error';
        }
    }

    function startPolling(taskId) {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }

        statusDiv.textContent = 'Проверка статуса...';
        statusDiv.classList.remove('hidden');

        // Initial check
        checkTaskStatus(taskId).then(status => {
            if (status === 'running' || status === 'pending') {
                // If the task is still running, start polling
                pollingInterval = setInterval(async () => {
                    const currentStatus = await checkTaskStatus(taskId);
                    if (currentStatus !== 'running' && currentStatus !== 'pending') {
                        clearInterval(pollingInterval);
                        pollingInterval = null;
                    }
                }, 5000);
            }
        });
    }

    // --- Initial Load ---

    // Загружаем LSI из localStorage при загрузке страницы
    loadLsiFromStorage();

    // Проверяем, есть ли запущенная задача при загрузке страницы
    const hybridData = JSON.parse(localStorage.getItem(hybridStorageKey)) || {};
    const runningTaskId = hybridData.lsiGenerationTaskId;
    if (runningTaskId && runningTaskId !== 'undefined') {
        startPolling(runningTaskId);
    }
});