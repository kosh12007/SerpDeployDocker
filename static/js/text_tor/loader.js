import { calculateAndStoreAverage } from './calculator.js';

document.addEventListener('DOMContentLoaded', function() {
    console.log('Загрузчик текстового анализатора TOR инициализирован');
    const tableBody = document.querySelector('tbody');

    function renderTable(data) {
        if (!tableBody || !data) return;
        tableBody.innerHTML = '';

        data.forEach(result => {
            const row = document.createElement('tr');
            row.setAttribute('data-result-url', result.url);
            
            let headingsHTML = 'N/A';
            if (result.headings) {
                try {
                    const headings = JSON.parse(result.headings);
                    headingsHTML = Array.isArray(headings) ? headings.map(h => `<span>H${h.level}: ${h.text}</span>`).join('<br>') : result.headings;
                } catch (e) {
                    headingsHTML = result.headings;
                }
            }

            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm"><a href="${result.url}" target="_blank" title="${result.url}" class="text-blue-500 hover:underline truncate-link">${result.url}</a></td>
                <td class="px-6 py-4 whitespace-normal text-sm" contenteditable="true" data-field="title">${result.title || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-normal text-sm" contenteditable="true" data-field="description">${result.description || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm" contenteditable="true" data-field="text_length">${result.text_length || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <button class="toggle-content-btn text-blue-500 hover:underline">Показать/скрыть</button>
                    <div class="content-to-toggle hidden mt-2 p-2 border rounded" contenteditable="true" data-field="headings">${headingsHTML}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <button class="toggle-content-btn text-blue-500 hover:underline">Показать/скрыть</button>
                    <div class="content-to-toggle hidden mt-2 p-2 border rounded" contenteditable="true" data-field="lsi_words">
                        ${result.lsi_words ? ( (Array.isArray(JSON.parse(result.lsi_words))) ? JSON.parse(result.lsi_words).join('<br>') : result.lsi_words) : 'N/A'}
                    </div>
                </td>
            `;
            tableBody.appendChild(row);
        });
        
        calculateAndStoreAverage(data);
    }

    const urlParams = new URLSearchParams(window.location.search);
    const torData = JSON.parse(localStorage.getItem('torData'));
    const torResultsData = JSON.parse(localStorage.getItem('torResultsData'));

    if (urlParams.has('result_ids')) {
        console.log('ID результатов в URL. Данные будут обработаны редактором.');
        return;
    }

    // Проверяем, изменились ли ID задач в torData по сравнению с torResultsData
    if (torData && torData.length > 0 && torResultsData && torResultsData.length > 0) {
        const torDataIds = new Set(torData.map(String));
        const torResultsDataIds = new Set(torResultsData.map(item => String(item.id)));
        
        // Проверяем, изменились ли ID задач - если наборы ID различаются, сбрасываем torResultsData
        const torDataChanged = torDataIds.size !== torResultsDataIds.size ||
                              ![...torDataIds].every(id => torResultsDataIds.has(id)) ||
                              ![...torResultsDataIds].every(id => torDataIds.has(id));

        if (torDataChanged) {
            console.log('ID задач изменились. Сбрасываем torResultsData и записываем новые данные.');
            // Сбрасываем torResultsData, так как ID задач изменились
            localStorage.removeItem('torResultsData');
            
            // Перенаправляем для загрузки новых данных с сервера
            const queryParams = new URLSearchParams();
            torData.forEach(id => queryParams.append('result_ids', id));
            window.location.search = queryParams.toString();
            return;
        }
        
        // Если ID не изменились, проверяем наличие всех элементов
        const allIdsPresent = [...torDataIds].every(id => torResultsDataIds.has(id));

        if (allIdsPresent) {
            console.log('Все ID найдены в localStorage. Рендеринг из localStorage.');
            const dataToDisplay = torResultsData.filter(item => torDataIds.has(String(item.id)));
            renderTable(dataToDisplay);
            return;
        }
    }

    if (torData && torData.length > 0) {
        console.log('Данные неполные. Перенаправление для загрузки с сервера.');
        const queryParams = new URLSearchParams();
        torData.forEach(id => queryParams.append('result_ids', id));
        window.location.search = queryParams.toString();
    } else {
        console.log('Нет ID в torData. Ничего не загружено.');
    }
});