/**
 * Модуль получения и отображения баланса API
 * Поддерживает десктопную и мобильную версию
 */
document.addEventListener('DOMContentLoaded', function () {
    // Десктопные элементы
    const balanceDisplay = document.getElementById('balance-display');
    const refreshButton = document.getElementById('refresh-balance-btn');

    // Мобильные элементы
    const balanceDisplayMobile = document.getElementById('balance-display-mobile');
    const refreshButtonMobile = document.getElementById('refresh-balance-btn-mobile');

    /**
     * Обновляет отображение баланса во всех элементах
     * @param {string} value - Значение для отображения
     */
    function updateBalanceDisplays(value) {
        if (balanceDisplay) {
            balanceDisplay.textContent = value;
        }
        if (balanceDisplayMobile) {
            balanceDisplayMobile.textContent = value;
        }
    }

    /**
     * Загружает баланс с сервера
     */
    function fetchBalance() {
        // Проверяем наличие хотя бы одного элемента отображения
        if (!balanceDisplay && !balanceDisplayMobile) return;

        updateBalanceDisplays('Загрузка...');

        fetch("/get-balance")
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.balance !== undefined) {
                    updateBalanceDisplays(data.balance);
                    localStorage.setItem('balance', data.balance);
                } else {
                    updateBalanceDisplays('Ошибка');
                }
            })
            .catch(error => {
                console.error('Ошибка при получении баланса:', error);
                updateBalanceDisplays('Ошибка');
            });
    }

    // Загрузка баланса при загрузке страницы
    fetchBalance();

    // Обновление баланса по клику на кнопку (десктоп)
    if (refreshButton) {
        refreshButton.addEventListener('click', fetchBalance);
    }

    // Обновление баланса по клику на кнопку (мобильная версия)
    if (refreshButtonMobile) {
        refreshButtonMobile.addEventListener('click', fetchBalance);
    }
});
