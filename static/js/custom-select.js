class CustomSelect {
    constructor(selector, options) {
        this.selectElement = document.querySelector(selector);
        if (!this.selectElement) {
            console.warn(`CustomSelect: element with selector "${selector}" not found.`);
            return;
        }

        this.options = {
            apiUrl: '',
            placeholder: 'Выберите значение',
            ...options
        };

        this.elements = {
            trigger: null,
            optionsContainer: null,
            searchInput: null,
            optionsList: null,
            hiddenInput: null,
            triggerSpan: null,
        };

        this.state = {
            currentPage: 1,
            isLoading: false,
            hasMore: true,
            debounceTimer: null,
        };

        this.init();
    }

    init() {
        this.createHtmlStructure();
        this.addEventListeners();
    }

    createHtmlStructure() {
        const wrapper = document.createElement('div');
        wrapper.className = 'custom-select-wrapper';

        const select = document.createElement('div');
        select.className = 'custom-select';
        
        const trigger = document.createElement('div');
        trigger.className = 'w-full p-2 border rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-200 border-gray-300 dark:border-gray-600 flex justify-between items-center cursor-pointer';
        trigger.innerHTML = `<span>${this.options.placeholder}</span><div class="arrow"></div>`;

        const optionsContainer = document.createElement('div');
        optionsContainer.className = 'custom-options absolute z-10 w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded mt-1 hidden';
        
        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.className = 'w-full p-2 border-b border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-200';
        searchInput.placeholder = 'Поиск...';
        
        const optionsList = document.createElement('div');
        optionsList.className = 'options-list max-h-60 overflow-y-auto';

        optionsContainer.appendChild(searchInput);
        optionsContainer.appendChild(optionsList);
        
        select.appendChild(trigger);
        select.appendChild(optionsContainer);
        
        const originalSelect = this.selectElement;
        this.elements.hiddenInput = document.createElement('input');
        this.elements.hiddenInput.type = 'hidden';
        this.elements.hiddenInput.name = originalSelect.name;
        
        wrapper.appendChild(select);
        wrapper.appendChild(this.elements.hiddenInput);
        
        originalSelect.replaceWith(wrapper);

        // Store references
        this.selectElement = wrapper.querySelector('.custom-select');
        this.elements.trigger = trigger;
        this.elements.optionsContainer = optionsContainer;
        this.elements.searchInput = searchInput;
        this.elements.optionsList = optionsList;
        this.elements.triggerSpan = trigger.querySelector('span');
    }

    addEventListeners() {
        this.elements.trigger.addEventListener('click', () => {
            this.toggle();
        });

        this.elements.searchInput.addEventListener('input', () => {
            clearTimeout(this.state.debounceTimer);
            this.state.debounceTimer = setTimeout(() => {
                this.state.currentPage = 1;
                this.state.hasMore = true;
                this.fetchData(this.elements.searchInput.value, false);
            }, 300);
        });

        this.elements.optionsList.addEventListener('scroll', () => {
            if (this.elements.optionsList.scrollTop + this.elements.optionsList.clientHeight >= this.elements.optionsList.scrollHeight - 5 && this.state.hasMore && !this.state.isLoading) {
                this.state.currentPage++;
                this.fetchData(this.elements.searchInput.value, true);
            }
        });

        this.elements.optionsList.addEventListener('click', (e) => {
            if (e.target.classList.contains('custom-option')) {
                this.selectOption(e.target);
            }
        });

        document.addEventListener('click', (e) => {
            if (!this.selectElement.contains(e.target)) {
                this.close();
            }
        });
    }

    fetchData(search = '', append = false) {
        if (this.state.isLoading) return;
        if (!append) this.state.currentPage = 1;
        if (!this.state.hasMore && append) return;

        this.state.isLoading = true;
        const url = `${this.options.apiUrl}?search=${encodeURIComponent(search)}&page=${this.state.currentPage}`;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (!append) {
                    this.elements.optionsList.innerHTML = '';
                }
                data.results.forEach(item => {
                    const option = document.createElement('div');
                    option.classList.add('custom-option', 'p-2', 'hover:bg-blue-500', 'hover:text-white', 'cursor-pointer', 'text-gray-900', 'dark:text-gray-200');
                    option.dataset.value = item.id;
                    option.textContent = item.text;
                    this.elements.optionsList.appendChild(option);
                });
                this.state.hasMore = data.pagination.more;
                this.state.isLoading = false;
            })
            .catch(error => {
                console.error('Ошибка загрузки данных:', error);
                this.state.isLoading = false;
            });
    }

    selectOption(optionElement) {
        const value = optionElement.dataset.value;
        const text = optionElement.textContent;

        this.elements.hiddenInput.value = value;
        this.elements.triggerSpan.textContent = text;

        const currentSelection = this.elements.optionsList.querySelector('.selection');
        if (currentSelection) {
            currentSelection.classList.remove('selection');
        }
        optionElement.classList.add('selection');
        this.close();
    }

    toggle() {
        this.selectElement.classList.toggle('open');
        if (this.selectElement.classList.contains('open')) {
            this.fetchData(this.elements.searchInput.value, false);
        }
    }

    close() {
        this.selectElement.classList.remove('open');
    }
    
    setDefault(id, text) {
        if (this.elements && this.elements.hiddenInput) {
            this.elements.hiddenInput.value = id;
            this.elements.triggerSpan.textContent = text;
            
            // You might want to add the option to the list if it's not there
            const option = document.createElement('div');
            option.classList.add('custom-option', 'selection');
            option.dataset.value = id;
            option.textContent = text;
            this.elements.optionsList.prepend(option);
        }
    }
}