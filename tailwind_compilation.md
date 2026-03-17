# Компиляция стилей с использованием Tailwind CSS

В проекте стили компилируются с использованием Tailwind CSS. Процесс компиляции настроен следующим образом:

### 1. Конфигурационные файлы:

-   `tailwind.config.js`: Основной конфигурационный файл Tailwind CSS, в котором определены настройки темной темы (`darkMode: 'class'`) и пути к файлам, содержащим классы Tailwind.
-   `postcss.config.js`: Конфигурация PostCSS с плагинами Tailwind CSS и Autoprefixer.

### 2. Входные CSS файлы:

-   `static/css/input-main.css`: Содержит директивы `@tailwind` и кастомные стили для основного интерфейса.
-   `static/css/input-theme-light.css`: Содержит директивы `@tailwind` и стили для светлой темы.
-   `static/css/input-theme-dark.css`: Содержит директивы `@tailwind` и стили для темной темы.
-   `static/css/input.css`: Базовый файл с директивами `@tailwind`.

### 3. Команды для компиляции (определены в `package.json`):

-   `build:main`: Компилирует основные стили: `tailwindcss -i ./static/css/input-main.css -o ./static/css/main.css --minify`
-   `build:theme-light`: Компилирует стили светлой темы: `tailwindcss -i ./static/css/input-theme-light.css -o ./static/css/theme-light.css --minify`
-   `build:theme-dark`: Компилирует стили темной темы: `tailwindcss -i ./static/css/input-theme-dark.css -o ./static/css/theme-dark.css --minify`
-   `build`: Выполняет все три команды компиляции.
-   `watch:main`, `watch:theme-light`, `watch:theme-dark`: Команды для наблюдения за изменениями в CSS-файлах и автоматической перекомпиляции.

### 4. Выходные CSS файлы:

-   `static/css/main.css`: Скомпилированные основные стили.
-   `static/css/theme-light.css`: Скомпилированные стили светлой темы.
-   `static/css/theme-dark.css`: Скомпилированные стили темной темы.

### 5. Процесс компиляции:

Процесс компиляции использует PostCSS с Autoprefixer для автоматического добавления вендорных префиксов. Также используется опция `--minify` для минификации результирующих CSS-файлов в продакшен-сборке.

Для запуска компиляции всех стилей выполните следующую команду в терминале:

```bash
npm run build