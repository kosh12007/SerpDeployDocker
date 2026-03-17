/**
 * Скрипт для автоматической загрузки URL-адресов из localStorage на страницу page_analyzer.html
 */

// Ожидаем полной загрузки DOM перед выполнением скрипта
document.addEventListener('DOMContentLoaded', function() {
    // Ключ для доступа к данным в localStorage
    const storageKey = 'selectedSitesForAnalysis';

    // Получаем textarea по имени 'urls'
    const urlsTextarea = document.querySelector('textarea[name="urls"]');

    // Проверяем, существует ли элемент textarea на странице
    if (!urlsTextarea) {
        // console.error('Элемент textarea с именем "urls" не найден на странице.');
        return; // Прерываем выполнение функции, если элемент не найден
    }

    try {
        // Проверяем, есть ли данные в localStorage по указанному ключу
        const storedUrlsJson = localStorage.getItem(storageKey);

        if (storedUrlsJson) {
            // Декодируем JSON-строку в массив
            const urlsArray = JSON.parse(storedUrlsJson);

            // Проверяем, является ли распарсенное значение массивом
            if (Array.isArray(urlsArray)) {
                // Преобразуем массив URL в строку, где каждый URL на новой строке
                const urlsString = urlsArray.join('\n');
                
                // Вставляем строки URL в textarea
                urlsTextarea.value = urlsString;

                // Очищаем localStorage от использованного ключа
                // localStorage.removeItem(storageKey);

                // console.log('URL-адреса успешно загружены из localStorage и вставлены в форму.');
            } else {
                // console.warn(`Данные в localStorage по ключу '${storageKey}' не являются массивом.`);
            }
        } else {
            // console.info(`Нет данных в localStorage по ключу '${storageKey}'.`);
        }
    } catch (error) {
        // Обрабатываем возможные ошибки при парсинге JSON или взаимодействии с localStorage
        // console.error('Произошла ошибка при загрузке URL из localStorage:', error);
    }

    // Добавляем обработчик события input для обновления localStorage
    urlsTextarea.addEventListener('input', function() {
        // Получаем текущее содержимое текстового поля
        const currentContent = urlsTextarea.value;

        // Разделяем содержимое на массив URL по символу новой строки
        let urlsArray = currentContent.split('\n');

        // Фильтруем пустые строки из массива
        urlsArray = urlsArray.filter(url => url.trim() !== '');

        // Сохраняем обновленный массив в localStorage под ключом 'selectedSitesForAnalysis' в формате JSON
        try {
            localStorage.setItem(storageKey, JSON.stringify(urlsArray));
            // console.log('Обновленный массив URL сохранен в localStorage.');
        } catch (error) {
            // console.error('Произошла ошибка при сохранении URL в localStorage:', error);
        }
    });
});