/**
 * Модуль калькулятора для страницы создания ТЗ на текст.
 */

/**
 * Рассчитывает средний объем текста из предоставленных данных,
 * отображает его на странице и сохраняет в localStorage.
 * @param {Array} data - Массив объектов с данными, каждый из которых должен иметь свойство text_length.
 */
export function calculateAndStoreAverage(data) {
    const avgTextValueCell = document.getElementById('average-text-value');
    const hybridStorageKey = 'hybridTorData';
    console.log()

    if (!data || data.length === 0) {
        if (avgTextValueCell) {
            avgTextValueCell.textContent = 'N/A';
        }
        return;
    }

    const totalLength = data.reduce((sum, item) => sum + (parseInt(item.text_length, 10) || 0), 0);
    const averageLength = Math.round(totalLength / data.length);
    
    if (avgTextValueCell) {
        avgTextValueCell.textContent = averageLength;
    }

    // Сохраняем в localStorage
    let hybridData = JSON.parse(localStorage.getItem(hybridStorageKey)) || {};
    hybridData.averageTextLength = averageLength;
    localStorage.setItem(hybridStorageKey, JSON.stringify(hybridData));
    console.log(`Средний объем текста (${averageLength}) сохранен в localStorage.`);
}