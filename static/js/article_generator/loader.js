document.addEventListener('DOMContentLoaded', function () {
    const transferData = JSON.parse(localStorage.getItem('transferData'));

    if (transferData) {
        document.getElementById('inspiration_example').value = transferData.urls || '';
        document.getElementById('keywords_primary').value = transferData.keyphrases || '';
        document.getElementById('length').value = transferData.average || '';
        document.getElementById('header_structure').value = transferData.headings || '';
        document.getElementById('keywords_lsi').value = transferData.lsi || '';

        // Очищаем данные после использования
        // localStorage.removeItem('transferData');

        Toastify({
            text: 'Данные со страницы "Создать ТЗ" успешно перенесены!',
            duration: 5000,
            close: true,
            gravity: "top",
            position: "center",
            style: {
                background: "#4CAF50",
            },
        }).showToast();
    }
});