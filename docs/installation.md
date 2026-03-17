## Установка и запуск

### 1. Клонирование репозитория

```bash
git clone <URL репозитория>
cd <имя папки проекта>
```

### 2. Установка зависимостей

#### Бэкенд (Python)

Для установки Python-зависимостей выполните следующий скрипт:

```bash
install_dependencies.bat
```

Или вручную, используя `pip`:

```bash
pip install -r requirements.txt
```

#### Фронтенд (Node.js)

Для установки зависимостей Node.js и сборки Tailwind CSS выполните:

```bash
npm install
npm run build
```

### 3. Настройка переменных окружения

Создайте файл `.env` в корне проекта и добавьте в него необходимые переменные, такие как данные для подключения к базе данных. Пример:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=serp
SECRET_KEY=your_secret_key
```

### 4. Запуск приложения

Для запуска приложения выполните:

```bash
python main.py
```

Приложение будет доступно по адресу `http://127.0.0.1:5000`.