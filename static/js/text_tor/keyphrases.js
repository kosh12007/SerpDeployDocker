/**
 * Модуль для работы с ключевыми фразами.
 */
document.addEventListener('DOMContentLoaded', function() {
    const keyphrasesInput = document.getElementById('keyphrases-input');
    const keyphrasesCount = document.getElementById('keyphrases-count');
    const hybridStorageKey = 'hybridTorData';

    // Загрузка данных из localStorage при инициализации
    let hybridData = JSON.parse(localStorage.getItem(hybridStorageKey)) || {};
    if (hybridData.keyphrases) {
        keyphrasesInput.value = hybridData.keyphrases.join('\n');
        updateCount();
    }

    // Обновление счетчика и сохранение данных при вводе
    keyphrasesInput.addEventListener('input', function() {
        updateCount();
        saveData();
    });

    function updateCount() {
        const phrases = keyphrasesInput.value.split('\n').filter(phrase => phrase.trim() !== '');
        keyphrasesCount.textContent = phrases.length;
    }

    function saveData() {
        const phrases = keyphrasesInput.value.split('\n').filter(phrase => phrase.trim() !== '');
        
        let hybridData = JSON.parse(localStorage.getItem(hybridStorageKey)) || {};
        hybridData.keyphrases = phrases;
        hybridData.keyphrasesCount = phrases.length;
        
        localStorage.setItem(hybridStorageKey, JSON.stringify(hybridData));
    }
});