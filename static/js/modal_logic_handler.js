/**
 * Обработчик логики для модальных окон
 * Позволяет регистрировать специфичные функции для разных типов модальных окон
 */

class ModalLogicHandler {
    constructor() {
        this.handlers = new Map();
    }

    /**
     * Регистрация обработчика для конкретного типа модального окна
     * @param {string} targetId - ID целевого элемента
     * @param {function} handler - Функция обработки
     */
    registerHandler(targetId, handler) {
        this.handlers.set(targetId, handler);
        // console.log(`Обработчик зарегистрирован для: ${targetId}`);
    }

    /**
     * Получение обработчика для конкретного типа модального окна
     * @param {string} targetId - ID целевого элемента
     * @returns {function|undefined}
     */
    getHandler(targetId) {
        return this.handlers.get(targetId);
    }
}

// Создание глобального экземпляра обработчика
window.modalLogicHandler = new ModalLogicHandler();