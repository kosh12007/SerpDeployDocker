document.addEventListener('DOMContentLoaded', function () {
    const generateBtn = document.getElementById('generate-headings-btn');
    const getLastTaskBtn = document.getElementById('get-last-task-headings-btn');
    const statusDiv = document.getElementById('headings-generation-status');
    const resultDiv = document.getElementById('headings-generation-result');
    resultDiv.style.textTransform = 'none'; // Сбрасываем трансформацию текста
    const hybridStorageKey = 'hybridTorData';
    let pollingInterval = null;

    // --- Helper Functions ---

    function parseHeadings(text) {
        if (!text) return [];
        return text.split('\n').map(line => line.trim()).filter(line => line).map(line => {
            const match = line.match(/H(\d+): (.*)/);
            if (match) {
                return {
                    level: parseInt(match[1], 10),
                    text: match[2].trim()
                };
            }
            return {
                level: 2,
                text: line
            }; // Default to H2 if no match
        });
    }

    function displayHeadings(headingsArray) {
        if (headingsArray && headingsArray.length > 0) {
            resultDiv.innerHTML = headingsArray.map(h => {
                const div = document.createElement('div');
                div.textContent = `H${h.level}: ${h.text}`;
                return div.innerHTML;
            }).join('<br>');
        } else {
            resultDiv.innerHTML = '';
        }
    }

    function loadHeadingsFromStorage() {
        const hybridData = JSON.parse(localStorage.getItem(hybridStorageKey)) || {};
        if (hybridData.generatedHeadings) {
            displayHeadings(hybridData.generatedHeadings);
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

            const averageTextLength = hybridTorData.averageTextLength || 1500;
            const blocks = Math.round(averageTextLength / 500);

            let allHeadings = [];
            torResultsData.forEach(item => {
                if (item.headings) {
                    try {
                        const headings = JSON.parse(item.headings);
                        headings.forEach(h => allHeadings.push(h.text));
                    } catch (e) {
                        console.error('Ошибка парсинга заголовков:', e);
                    }
                }
            });

            if (allHeadings.length === 0) {
                statusDiv.textContent = 'Ошибка: Не найдено ни одного заголовка для анализа.';
                return;
            }

            const system_prompt = `Создай иерархическую структуру заголовков (H2 и H3) для коммерческого текста. Исходные данные: У тебя есть семантическое ядро — список ключевых заголовков и подзаголовков. Планируемый общий объем текста статьи: ~${averageTextLength} символов. Ключевое правило пропорции: Один заголовок H2 должен вводить раздел текста объемом примерно 500 символов. Один заголовок H3 должен вводить подраздел текста объемом примерно 500 символов. Основное ограничение: Суммарный объем текста, на который приходятся все заголовки H2 и H3, должен быть равен ~${averageTextLength} символов. Это не длина самих заголовков, а объем контента, который они структурируют. Математика для ИИ (конкретное руководство к действию): Рассчитай, сколько всего условных "блоков" по 500 символов у нас есть: ${averageTextLength} / 500 = ${blocks} блоков. Конечная инструкция: Используя предоставленный список заголовков, собери логичную иерархическую структуру (H2 > H3), которая точно соответствует любой комбинации, дающей в сумме ${blocks} блоков. Структура должна быть смысловой, а не просто математической. Последним заголовком h2 должен быть призыв к действию, типа "Почему с нами выгодно работать". Результат выдай без пояснений, только заголовки формата H1: Заголовок 1, H2: Заголовок 2 итак далее`;
            const user_message = `Список заголовков: ${allHeadings.join(', ')}`;

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
                hybridData.headingsGenerationTaskId = taskId;
                localStorage.setItem(hybridStorageKey, JSON.stringify(hybridData));
                statusDiv.textContent = `Задача ${taskId} создана. Ожидание результата...`;
                Toastify({
                    text: data.message || "Задача успешно создана",
                    duration: 3000,
                    style: {
                        background: "#4CAF50"
                    },
                }).showToast();
                pollTaskStatus(taskId); // Начинаем опрос
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
        const taskId = hybridData.headingsGenerationTaskId;
        if (!taskId) {
            statusDiv.textContent = 'ID последней задачи не найден.';
            return;
        }
        pollTaskStatus(taskId);
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
                delete hybridTorData.headingsGenerationTaskId;
                delete hybridTorData.generatedHeadings;
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

                const safeResponse = data.ai_response ? data.ai_response : '';
                const tempDiv = document.createElement('div');
                tempDiv.textContent = safeResponse;
                resultDiv.innerHTML = tempDiv.innerHTML.replace(/\n/g, '<br>');
                resultDiv.classList.remove('hidden');

                let hybridTorData = JSON.parse(localStorage.getItem(hybridStorageKey)) || {};
                const headingsArray = parseHeadings(data.ai_response);
                hybridTorData.generatedHeadings = headingsArray;
                localStorage.setItem(hybridStorageKey, JSON.stringify(hybridTorData));
                displayHeadings(headingsArray);

                return 'completed';

            } else if (data.status === 'error') {
                statusDiv.textContent = `Ошибка выполнения задачи ${taskId}: ${data.message}`;
                return 'error';
            }

            return data.status;
        } catch (error) {
            statusDiv.textContent = `Ошибка опроса статуса: ${error.message}`;
            console.error(error);
            return 'error';
        }
    }

    function pollTaskStatus(taskId) {
        if (pollingInterval) clearInterval(pollingInterval);

        statusDiv.textContent = 'Проверка статуса...';
        statusDiv.classList.remove('hidden');

        checkTaskStatus(taskId).then(status => {
            if (pollingInterval) clearInterval(pollingInterval); // Safety check in case another poll started

            if (status !== 'running' && status !== 'pending') {
                return;
            }

            pollingInterval = setInterval(async () => {
                const currentStatus = await checkTaskStatus(taskId);
                if (currentStatus !== 'running' && currentStatus !== 'pending') {
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                }
            }, 5000);
        });
    }

    // Загружаем заголовки из localStorage при загрузке страницы
    loadHeadingsFromStorage();

    // Проверяем, есть ли запущенная задача при загрузке страницы
    const hybridData = JSON.parse(localStorage.getItem(hybridStorageKey)) || {};
    const runningTaskId = hybridData.headingsGenerationTaskId;
    if (runningTaskId && runningTaskId !== 'undefined') {
        // Проверяем статус сразу для любой задачи
        pollTaskStatus(runningTaskId);
    }
});