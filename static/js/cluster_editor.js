document.addEventListener('DOMContentLoaded', function () {
    const clustersContainer = document.getElementById('clusters-container');
    const createEmptyGroupBtn = document.getElementById('create-empty-group');
    const viewModeGridBtns = document.querySelectorAll('.view-mode-grid-btn');
    const viewModeListBtns = document.querySelectorAll('.view-mode-list-btn');

    /**
     * Отображает уведомление об ошибке.
     * @param {string} message - Сообщение об ошибке.
     */
    function showError(message) {
        // В реальном проекте здесь может быть более сложная система уведомлений.
        alert(message);
    }

    /**
     * Отправляет асинхронный запрос к API.
     * @param {string} url - URL эндпоинта.
     * @param {string} method - HTTP-метод ('POST', 'DELETE', etc.).
     * @param {object} body - Тело запроса.
     * @returns {Promise<object>} - Ответ от сервера в формате JSON.
     */
    async function fetchAPI(url, method, body) {
        try {
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify(body),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || 'Произошла ошибка');
            }
            return await response.json();
        } catch (error) {
            showError(error.message);
            throw error; // Пробрасываем ошибку дальше для обработки в вызывающем коде
        }
    }

    /**
     * Обновляет счетчик суммарной частотности для группы.
     * @param {HTMLElement} groupCard - Карточка группы.
     */
    function updateTotalVolume(groupCard) {
        const totalVolumeEl = groupCard.querySelector('.total-volume');
        if (!totalVolumeEl) return;

        const keywords = groupCard.querySelectorAll('.keyword-item');
        const totalVolume = Array.from(keywords).reduce((sum, item) => {
            return sum + parseInt(item.dataset.volume, 10);
        }, 0);

        totalVolumeEl.textContent = `Общая частотность: ${totalVolume}`;
    }

    /**
     * Создает HTML-элемент для ключевого слова.
     * @param {object} query - Объект запроса { id, text, volume }.
     * @returns {HTMLElement} - Готовый li элемент.
     */
    function createKeywordElement(query) {
        const item = document.createElement('li');
        item.className = 'keyword-item bg-gray-200 dark:bg-gray-700 p-2 rounded-md mb-2 cursor-move flex justify-between items-center';
        item.dataset.id = query.id;
        item.dataset.volume = query.volume || 0;

        const nameSpan = document.createElement('span');
        nameSpan.textContent = query.name;

        const volumeSpan = document.createElement('span');
        volumeSpan.className = 'text-sm text-gray-500';
        volumeSpan.textContent = query.volume || 0;

        item.appendChild(nameSpan);
        item.appendChild(volumeSpan);

        return item;
    }

    /**
     * Создает карточку группы (кластера).
     * @param {object} group - Данные группы { id, name, keywords }.
     * @param {boolean} isUnclustered - Является ли это группой некластеризованных.
     */
    function createGroupCard(group, isUnclustered = false) {
        const card = document.createElement('div');
        card.className = 'group-card bg-white dark:bg-gray-800 p-4 rounded-lg shadow-md';
        card.dataset.groupId = group.id !== null ? group.id : 'null';

        const keywordsList = document.createElement('ul');
        keywordsList.className = 'keywords-list min-h-[50px]';
        keywordsList.dataset.groupId = group.id !== null ? group.id : 'null';

        // Header construction
        const header = document.createElement('div');
        header.className = 'group-header flex justify-between items-center mb-4';

        const titleDiv = document.createElement('h2');
        titleDiv.className = 'group-title-text text-xl font-semibold text-gray-700 dark:text-gray-300';

        if (isUnclustered) {
            titleDiv.textContent = group.name;
            header.appendChild(titleDiv);
        } else {
            const titleSpan = document.createElement('span');
            titleSpan.textContent = group.name;
            titleDiv.appendChild(titleSpan);
            header.appendChild(titleDiv);

            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'flex items-center space-x-2';

            const renameBtn = document.createElement('button');
            renameBtn.className = 'rename-group-btn text-gray-500 hover:text-blue-500';
            renameBtn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.536L16.732 3.732z"></path></svg>';

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'delete-group-btn text-gray-500 hover:text-red-500';
            deleteBtn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>';

            actionsDiv.appendChild(renameBtn);
            actionsDiv.appendChild(deleteBtn);
            header.appendChild(actionsDiv);
        }

        card.appendChild(header);

        if (!isUnclustered) {
            const totalVolumeDiv = document.createElement('div');
            totalVolumeDiv.className = 'total-volume font-bold text-gray-600 dark:text-gray-400 mb-2';
            // Will be populated later
            card.appendChild(totalVolumeDiv);
        }

        card.appendChild(keywordsList);

        if (Array.isArray(group.queries)) {
            group.queries.forEach(query => {
                if (query) {
                    keywordsList.appendChild(createKeywordElement(query));
                }
            });
        }

        clustersContainer.appendChild(card);

        const totalVolumeEl = card.querySelector('.total-volume');
        if (totalVolumeEl) {
            totalVolumeEl.textContent = `Общая частотность: ${group.total_volume || 0}`;
        }
    }

    /**
     * Инициализация SortableJS для всех списков.
     */
    function initSortable() {
        const lists = document.querySelectorAll('.keywords-list');
        lists.forEach(list => {
            new Sortable(list, {
                group: 'keywords',
                animation: 150,
                onEnd: async function (evt) {
                    const item = evt.item;
                    const toList = evt.to;
                    const fromList = evt.from;

                    const keywordId = item.dataset.id;
                    const targetGroupId = toList.dataset.groupId;

                    try {
                        await fetchAPI('/api/clusters/move-keyword', 'POST', {
                            keyword_id: keywordId,
                            target_group_id: targetGroupId
                        });

                        // Обновляем счетчики
                        const fromCard = fromList.closest('.group-card');
                        const toCard = toList.closest('.group-card');
                        if (fromCard) updateTotalVolume(fromCard);
                        if (toCard) updateTotalVolume(toCard);

                    } catch (error) {
                        // Если API вернуло ошибку, возвращаем элемент обратно
                        fromList.appendChild(item);
                        showError('Не удалось переместить ключевое слово.');
                    }
                },
            });
        });
    }

    /**
     * Обработчик переименования группы.
     * @param {Event} e - Событие клика.
     */
    async function handleRenameGroup(e) {
        const renameBtn = e.target.closest('.rename-group-btn');
        if (!renameBtn) return;

        const card = renameBtn.closest('.group-card');
        const titleSpan = card.querySelector('.group-title-text span');
        const originalName = titleSpan.textContent;

        const input = document.createElement('input');
        input.type = 'text';
        input.value = originalName;
        input.className = 'text-xl font-semibold bg-transparent border-b-2 border-blue-500 focus:outline-none';

        titleSpan.replaceWith(input);
        input.focus();
        input.select();

        const saveName = async () => {
            const newName = input.value.trim();
            if (newName && newName !== originalName) {
                const groupId = card.dataset.groupId;
                try {
                    await fetchAPI('/api/clusters/rename', 'POST', {
                        group_id: groupId,
                        new_name: newName
                    });
                    const newTitleSpan = document.createElement('span');
                    newTitleSpan.textContent = newName;
                    input.replaceWith(newTitleSpan);
                } catch (error) {
                    showError('Не удалось переименовать группу.');
                    input.replaceWith(titleSpan); // Возвращаем старое имя в случае ошибки
                }
            } else {
                input.replaceWith(titleSpan); // Если имя не изменилось
            }
        };

        input.addEventListener('blur', saveName);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                input.blur();
            } else if (e.key === 'Escape') {
                input.removeEventListener('blur', saveName);
                input.replaceWith(titleSpan);
            }
        });
    }

    /**
     * Обработчик удаления группы.
     * @param {Event} e - Событие клика.
     */
    async function handleDeleteGroup(e) {
        const deleteBtn = e.target.closest('.delete-group-btn');
        if (!deleteBtn) return;

        const card = deleteBtn.closest('.group-card');
        const groupId = card.dataset.groupId;
        const groupName = card.querySelector('.group-title-text span').textContent;

        if (confirm(`Вы уверены, что хотите удалить группу "${groupName}"? Все ключевые слова будут перемещены в "Некластеризованные".`)) {
            try {
                await fetchAPI('/api/clusters/delete', 'DELETE', { group_id: groupId });

                // Перемещаем ключевые слова в некластеризованные
                const keywords = card.querySelectorAll('.keyword-item');
                const unclusteredList = document.querySelector('.keywords-list[data-group-id="null"]');

                keywords.forEach(kw => unclusteredList.appendChild(kw));

                // Обновляем счетчик у некластеризованных (если он есть)
                const unclusteredCard = unclusteredList.closest('.group-card');
                if (unclusteredCard) updateTotalVolume(unclusteredCard);

                card.remove(); // Удаляем карточку группы
            } catch (error) {
                showError('Не удалось удалить группу.');
            }
        }
    }

    /**
     * Обработчик создания пустой группы.
     */
    async function handleCreateEmptyGroup() {
        const groupName = prompt("Введите название новой группы:", "Новая группа");
        if (groupName && groupName.trim()) {
            try {
                const projectId = clustersContainer.dataset.projectId;
                const result = await fetchAPI('/api/clusters/create', 'POST', {
                    name: groupName.trim(),
                    project_id: projectId
                });
                const newGroup = {
                    id: result.group_id,
                    name: groupName.trim(),
                    keywords: []
                };
                createGroupCard(newGroup);
                initSortable(); // Переинициализация, чтобы новая карточка стала целью для перетаскивания
            } catch (error) {
                showError('Не удалось создать группу.');
            }
        }
    }

    /**
     * Устанавливает режим отображения (сетка или список).
     * @param {'grid' | 'list'} mode - Режим отображения.
     */
    function setViewMode(mode) {
        if (mode === 'list') {
            clustersContainer.classList.remove('grid', 'md:grid-cols-2', 'lg:grid-cols-3');
            clustersContainer.classList.add('flex', 'flex-col');
            viewModeListBtns.forEach(btn => btn.classList.add('bg-white', 'dark:bg-gray-500', 'shadow', 'text-blue-600'));
            viewModeGridBtns.forEach(btn => btn.classList.remove('bg-white', 'dark:bg-gray-500', 'shadow', 'text-blue-600'));
        } else { // grid
            clustersContainer.classList.remove('flex', 'flex-col');
            clustersContainer.classList.add('grid', 'md:grid-cols-2', 'lg:grid-cols-3');
            viewModeGridBtns.forEach(btn => btn.classList.add('bg-white', 'dark:bg-gray-500', 'shadow', 'text-blue-600'));
            viewModeListBtns.forEach(btn => btn.classList.remove('bg-white', 'dark:bg-gray-500', 'shadow', 'text-blue-600'));
        }
        // Сохраняем выбор в localStorage
        localStorage.setItem('cluster_view_mode', mode);
    }

    // --- Инициализация ---

    // 1. Устанавливаем начальный режим отображения
    const savedViewMode = localStorage.getItem('cluster_view_mode') || 'grid';
    setViewMode(savedViewMode);

    // 2. Создаем карточки для существующих групп
    // console.log("Полученные данные групп:", groupsData);
    groupsData.forEach(group => {
        // console.log("Обработка группы:", group);
        createGroupCard(group)
    });

    // 2. Создаем карточку для некластеризованных запросов
    // console.log("Некластеризованные данные:", unclusteredQueriesData);
    createGroupCard({
        id: 'null', // Специальный ID для некластеризованной группы
        name: 'Некластеризованные запросы',
        queries: unclusteredQueriesData
    }, true);

    // 3. Инициализируем Drag-and-Drop
    initSortable();

    // 5. Навешиваем обработчики событий
    clustersContainer.addEventListener('click', handleRenameGroup);
    clustersContainer.addEventListener('click', handleDeleteGroup);
    createEmptyGroupBtn.addEventListener('click', handleCreateEmptyGroup);
    viewModeGridBtns.forEach(btn => btn.addEventListener('click', () => setViewMode('grid')));
    viewModeListBtns.forEach(btn => btn.addEventListener('click', () => setViewMode('list')));
});
