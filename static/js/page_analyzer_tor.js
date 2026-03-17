/**
 * Обработчик для создания задачи TOR
 * Реализует делегирование событий для кнопок с классом create-tor-btn
 */
document.addEventListener('click', function(event) {
    // Проверяем, была ли нажата кнопка с классом create-tor-btn
    if (event.target.classList.contains('analyze-selected-sites-btn')) {
        // Находим ближайший родительский элемент с классом task-content
        const taskContent = event.target.closest('.task-content');
        console.log("Найден taskContent:", taskContent);
        if (taskContent) {
            // Находим все отмеченные чекбоксы с классом .result-checkbox внутри task-content
            const checkedCheckboxes = taskContent.querySelectorAll('input.result-checkbox:checked');
            console.log("Найдено отмеченных чекбоксов:", checkedCheckboxes.length);
            
            // Проверяем, есть ли отмеченные чекбоксы
            if (checkedCheckboxes.length === 0) {
                Toastify({
                    text: "Не выбрано ни одной ссылки для анализа.",
                    duration: 2000,
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
            
            // Создаем массив для хранения ID результатов
            const selectedResultIds = [];
            
            // Обрабатываем каждый отмеченный чекбокс
            checkedCheckboxes.forEach(checkbox => {
                // Получаем ID результата из атрибута data-result-id
                const resultId = checkbox.getAttribute('data-result-id');
                selectedResultIds.push(resultId);
            });
            
            console.log("Выбранные ID результатов:", selectedResultIds);
            
            // Проверяем, есть ли данные для сохранения
            if (selectedResultIds.length === 0) {
                alert("Не удалось получить ID выбранных элементов. Пожалуйста, попробуйте снова.");
                return;
            }
            
            // Сохраняем массив ID в localStorage под ключом torData в формате JSON
            localStorage.setItem('torData', JSON.stringify(selectedResultIds));
            
            // Перенаправляем пользователя на страницу /text-tor/create
            window.location.href = '/text-tor/create';
        } else {
            console.error("Не найден элемент с классом task-content");
        }
    }
});