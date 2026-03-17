document.addEventListener('DOMContentLoaded', function () {

    function copyToClipboard(text, button) {
        if (!text) {
            showToast('Нет данных для копирования', 'error');
            return;
        }
        navigator.clipboard.writeText(text).then(function () {
            const originalText = button.innerHTML;
            button.textContent = 'Скопировано!';
            setTimeout(() => {
                button.innerHTML = originalText;
            }, 2000);
            showToast('Данные скопированы в буфер обмена');
        }, function (err) {
            showToast('Не удалось скопировать данные', 'error');
            console.error('Ошибка копирования: ', err);
        });
    }

    function showToast(message, type = 'success') {
        Toastify({
            text: message,
            duration: 3000,
            close: true,
            gravity: "top",
            position: "center",
            style: {
                background: type === 'success' ? "#4CAF50" : "#EF4444",
            },
        }).showToast();
    }

    // Копирование URL-ов
    document.getElementById('copy-urls-btn').addEventListener('click', function () {
        const urls = Array.from(document.querySelectorAll('tbody tr[data-result-url]'))
            .map(row => row.getAttribute('data-result-url'));
        copyToClipboard(urls.join('\n'), this);
    });

    // Копирование ключевых фраз
    document.getElementById('copy-keyphrases-btn').addEventListener('click', function () {
        const text = document.getElementById('keyphrases-input').value;
        // const phrases = text.split('\n').filter(p => p.trim() !== '');
        // copyToClipboard(phrases.join(', '), this);
        copyToClipboard(text, this); //Если нужно копировать данные через "," то раскомментируем строки выше а эту закомментируем
    });

    // Копирование среднего значения
    document.getElementById('copy-average-btn').addEventListener('click', function () {
        const text = document.getElementById('average-text-value').textContent;
        copyToClipboard(text, this);
    });

    // Копирование сгенерированных заголовков
    document.getElementById('copy-headings-btn').addEventListener('click', function () {
        const headingsDiv = document.getElementById('headings-generation-result');
        // const headings = headingsDiv.innerText.split('\n').filter(h => h.trim() !== '');
        // copyToClipboard(headings.join(', '), this);
        const headings = headingsDiv.innerText.split(',').filter(h => h.trim() !== '');//Если нужно копировать данные через "," то раскомментируем строки выше а эту закомментируем
        copyToClipboard(headings.join('\n'), this);//Если нужно копировать данные через "," то раскомментируем строки выше а эту закомментируем
    });
    // Копирование сгенерированных LSI
    document.getElementById('copy-lsi-btn').addEventListener('click', function () {
        const lsiDiv = document.getElementById('lsi-generation-result');
        // const lsi = lsiDiv.innerText.split('\n').filter(l => l.trim() !== '');
        // copyToClipboard(lsi.join(', '), this);
        const lsi = lsiDiv.innerText.split(',').filter(l => l.trim() !== ''); //Если нужно копировать данные через "," то раскомментируем строку выше а эту закомментируем
        copyToClipboard(lsi.join('\n'), this); //Если нужно копировать данные через "," то раскомментируем строку выше а эту закомментируем
    });

    // Перенос данных в генератор статей
    document.getElementById('transfer-to-generator-btn').addEventListener('click', function () {
        const urls = Array.from(document.querySelectorAll('tbody tr[data-result-url]'))
            .map(row => row.getAttribute('data-result-url'));
        
        const keyphrasesText = document.getElementById('keyphrases-input').value;
        const keyphrases = keyphrasesText.split('\n').filter(p => p.trim() !== '');

        const average = document.getElementById('average-text-value').textContent;

        const headingsDiv = document.getElementById('headings-generation-result');
        const headings = headingsDiv.innerText.split('\n').filter(h => h.trim() !== '');

        const lsiDiv = document.getElementById('lsi-generation-result');
        const lsi = lsiDiv.innerText.split('\n').filter(l => l.trim() !== '');

        const dataToTransfer = {
            urls: urls.join('\n'),
            keyphrases: keyphrases.join('\n'),
            average: average,
            headings: headings.join('\n'),
            lsi: lsi.join('\n')
        };

        localStorage.setItem('transferData', JSON.stringify(dataToTransfer));
        showToast('Данные подготовлены. Перенаправление...');
        
        window.location.href = '/article-generator';
    });
});