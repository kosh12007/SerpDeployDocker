document.addEventListener('DOMContentLoaded', function() {
    // Используем делегирование событий для кнопок с классом analyze-selected-sites-btn
    document.addEventListener('click', function(event) {
        // Проверяем, была ли нажата кнопка с нужным классом
        if (event.target.classList.contains('analyze-selected-sites-btn')) {
            // Находим родительский элемент task-content для этой кнопки
            const taskContent = event.target.closest('.task-content');
            if (taskContent) {
                // Собираем значения отмеченных чекбоксов только внутри этого блока task-content
                const checkedCheckboxes = taskContent.querySelectorAll('input[type="checkbox"]:checked');
                // console.log(`Найдено отмеченных чекбоксов: ${checkedCheckboxes.length}`); // Логирование для отладки
                
                const selectedUrls = Array.from(checkedCheckboxes).map(checkbox => checkbox.value);
                // console.log(`Выбранные URL:`, selectedUrls); // Логирование для отладки
                // Удаляем дубликаты из массива URL перед сохранением
                const uniqueSites = [...new Set(selectedUrls)];
                // console.log(`Уникальные URL:`, uniqueSites); // Логирование для отладки
                
                // Проверяем, есть ли выбранные сайты для анализа
                if (uniqueSites.length === 0) {
                    // Показываем уведомление, если нет выбранных сайтов
                    Toastify({
                        text: "Не выбрано ни одной ссылки для анализа.",
                        duration: 3000,
                        close: true,
                        gravity: "top",
                        position: "center",
                        style: {
                            background: "#EF4444" // Красный цвет
                        },
                        stopOnFocus: true
                    }).showToast();
                    return; // Прерываем выполнение, не перенаправляем
                }
                
                // Сохраняем уникальные URL в localStorage
                localStorage.setItem('selectedSitesForAnalysis', JSON.stringify(uniqueSites));
                
                // Перенаправляем пользователя на страницу анализа
                window.location.href = '/page-analyzer';
            } else {
                console.error('Не найден родительский элемент .task-content для кнопки');
            }
        }
    });
});