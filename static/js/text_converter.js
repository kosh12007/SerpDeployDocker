document.addEventListener('DOMContentLoaded', function () {
    const textInput = document.getElementById('text-input');
    const toolResult = document.getElementById('tool-result');
    const modeField = document.getElementById('mode-field');
    const wordDelimiterField = document.getElementById('word-delimiter-field');
    const caseField = document.getElementById('case-field');
    const copyResultBtn = document.getElementById('copy-result-btn');
    const saveStatus = document.getElementById('save-status');

    // Transliteration rules
    // 1. URL transliteration (SEO friendly)
    const urlTranslitMap = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e', 'ж': 'zh',
        'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
        'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts',
        'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E', 'Ж': 'Zh',
        'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O',
        'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts',
        'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    };

    // 2. Passport transliteration (ICAO DOC 9303 standard for Russian passports)
    const passportTranslitMap = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e', 'ж': 'zh',
        'з': 'z', 'и': 'i', 'й': 'i', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
        'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts',
        'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': 'ie', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'iu', 'я': 'ia',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E', 'Ж': 'ZH',
        'З': 'Z', 'И': 'I', 'Й': 'I', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O',
        'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'KH', 'Ц': 'TS',
        'Ч': 'CH', 'Ш': 'SH', 'Щ': 'SHCH', 'Ъ': 'IE', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'IU', 'Я': 'IA'
    };

    // Load saved data from localStorage to protect against accidental refreshes
    const savedText = localStorage.getItem('text_converter_input');
    const savedMode = localStorage.getItem('text_converter_mode');
    const savedDelimiter = localStorage.getItem('text_converter_delimiter');
    const savedCase = localStorage.getItem('text_converter_case');

    if (savedText) textInput.value = savedText;
    if (savedMode) modeField.value = savedMode;
    if (savedDelimiter) wordDelimiterField.value = savedDelimiter;
    if (savedCase) caseField.value = savedCase;

    // Process text dynamically
    function processText() {
        const text = textInput.value;
        const mode = modeField.value;
        const delimiterOption = wordDelimiterField.value;
        const caseOption = caseField.value;

        // Save options
        localStorage.setItem('text_converter_mode', mode);
        localStorage.setItem('text_converter_delimiter', delimiterOption);
        localStorage.setItem('text_converter_case', caseOption);

        if (!text) {
            toolResult.value = '';
            return;
        }

        let result = text;
        const translitMap = mode === 'url' ? urlTranslitMap : passportTranslitMap;

        // 1. Transliteration
        let transliterated = '';
        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            transliterated += translitMap[char] !== undefined ? translitMap[char] : char;
        }
        result = transliterated;

        // 2. URL parsing & specific replacement (only for URL mode)
        if (mode === 'url') {
            // Replace spaces and special chars (keep alphanumeric and spaces/dashes)
            result = result.replace(/[^\w\sа-яА-ЯёЁ_\\-]/gi, ' ');
            // Trim extra spaces
            result = result.replace(/\s+/g, ' ').trim();
        } else if (mode === 'passport') {
            // For passport, usually simply spaces or strict rules.
            // Replacing non alpha/numeric can be less strict, but let's keep it clean
            result = result.replace(/[^\w\sа-яА-ЯёЁ_\\-]/gi, ' ');
            result = result.replace(/\s+/g, ' ').trim();
        }

        // 3. Case
        if (caseOption === 'lower') {
            result = result.toLowerCase();
        } else if (caseOption === 'upper') {
            result = result.toUpperCase();
        } else if (caseOption === 'camel') {
            let words = result.toLowerCase().split(/\s+/);
            result = words.map((word, index) => {
                if (index === 0) return word;
                if (!word) return word;
                return word.charAt(0).toUpperCase() + word.slice(1);
            }).join(' ');
        }

        // 4. Delimiter
        let delimiter = '';
        if (delimiterOption === 'hyphen') {
            delimiter = '-';
        } else if (delimiterOption === 'underline') {
            delimiter = '_';
        } else if (delimiterOption === 'space') {
            delimiter = ' ';
        } else if (delimiterOption === 'none') {
            delimiter = '';
        }

        // Apply delimiter (replace spaces with delimiter)
        if (delimiterOption !== 'space') {
            result = result.replace(/\s/g, delimiter);
        }

        // In URL mode if there's custom delimiter, multiple dashes may form, clean them
        if (mode === 'url' && delimiter === '-') {
            result = result.replace(/-+/g, '-');
        } else if (mode === 'url' && delimiter === '_') {
            result = result.replace(/_+/g, '_');
        }

        toolResult.value = result;
    }

    // Protection logic: save to localStorage with indication
    let saveTimeout;
    textInput.addEventListener('input', function () {
        localStorage.setItem('text_converter_input', this.value);
        
        saveStatus.classList.remove('opacity-0');
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(() => {
            saveStatus.classList.add('opacity-0');
        }, 2000);

        processText();
    });

    modeField.addEventListener('change', processText);
    wordDelimiterField.addEventListener('change', processText);
    caseField.addEventListener('change', processText);

    // Initial process
    processText();

    // Copy to clipboard
    copyResultBtn.addEventListener('click', function () {
        if (!toolResult.value) return;
        
        // Native copy
        toolResult.select();
        toolResult.setSelectionRange(0, 99999); // For mobile devices
        
        try {
            document.execCommand('copy');
            const originalText = copyResultBtn.querySelector('span').textContent;
            copyResultBtn.querySelector('span').textContent = 'Скопировано!';
            setTimeout(() => {
                copyResultBtn.querySelector('span').textContent = originalText;
            }, 2000);
        } catch (err) {
            console.error('Failed to copy', err);
            // Fallback
            navigator.clipboard.writeText(toolResult.value).then(() => {
                const originalText = copyResultBtn.querySelector('span').textContent;
                copyResultBtn.querySelector('span').textContent = 'Скопировано!';
                setTimeout(() => {
                    copyResultBtn.querySelector('span').textContent = originalText;
                }, 2000);
            });
        }
    });
});
