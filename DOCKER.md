# Развёртывание в Docker

## Структура файлов

```
├── Dockerfile                    # Образ Flask-приложения
├── docker-compose.yml            # DEV: http://localhost
├── docker-compose.prod.yml       # PROD: VPS с доменом (HTTPS)
├── .env.example                  # Шаблон переменных (скопировать в .env)
├── .dockerignore                 # Исключения для образа
├── init-vps.sh                   # Скрипт первоначальной настройки VPS
└── docker/
    ├── entrypoint.sh             # Старт: ждёт MySQL → gunicorn
    └── nginx/
        ├── nginx.dev.conf        # Nginx для DEV (HTTP)
        └── nginx.prod.conf.template # Шаблон Nginx для PROD (HTTPS) с подстановкой DOMAIN
```

---

## 🖥️ DEV — локальная разработка (без домена)

Используется для разработки и тестирования проекта на локальном компьютере.
В этом режиме проект доступен по `http://localhost`, используется конфигурация без генерации SSL сертификатов.

### Требования

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (или Docker Engine)
- Docker Compose

### Шаг 1: Создать `.env`

```bash
cp .env.example .env
```

Заполнить базовые переменные в `.env`:

- `DB_PASSWORD` — любой пароль для MySQL
- `MYSQL_ROOT_PASSWORD` — root-пароль MySQL
- `SECRET_KEY` — сгенерировать: `python -c "import secrets; print(secrets.token_hex(24))"`
- `API_KEY` — ключ от сервисов, если требуются.
*(переменные `DOMAIN` и `LETSENCRYPT_EMAIL` для локального запуска не обязательны)*

### Шаг 2: Запустить локально

```bash
docker-compose up -d --build
```
*(важно использовать `docker-compose.yml`, который применяется по умолчанию при этой команде)*

### Шаг 3: Открыть

Перейдите в браузере:
```
http://localhost
```

### Полезные команды

```bash
# Посмотреть логи
docker-compose logs -f web
docker-compose logs -f nginx

# Остановить
docker-compose down

# Остановить и удалить данные БД
docker-compose down -v

# Перезапустить только web
docker-compose restart web
```

---

## 🌐 PROD — деплой на VPS (с привязкой домена)

Используется для боевого сервера. В этом режиме **автоматически** генерируются рабочие HTTPS сертификаты через Let's Encrypt и происходит привязка домена через обновленный `nginx.prod.conf.template`.

### Требования

- VPS/сервер с Ubuntu 22.04 (или подобный Linux-сервер)
- Установленные `docker` и `docker-compose`
- Созданная и обновленная A-запись DNS вашего домена: `ВАШ_ДОМЕН` → IP сервера

### Шаг 1: Скопировать проект на сервер

```bash
# Например через scp или git clone
scp -r ./serp_docker root@server:/srv/serp
```

### Шаг 2: Настроить переменные окружения

Перейдите в папку с проектом на сервере:
```bash
cd /srv/serp
cp .env.example .env
nano .env
```

В файле `.env` **ОБЯЗАТЕЛЬНО** задайте:

```env
DOMAIN=вашдомен.ru
LETSENCRYPT_EMAIL=ваш_email@example.com
MODE=hosting
```
*(Также не забудьте надежные пароли для базы данных и Secret Key)*

### Шаг 3: Автоматический запуск и получение SSL

Мы подготовили специальный скрипт `init-vps.sh`, который за одну команду запустит сервер, получит сертификаты и привяжет домен.

Делаем скрипт исполняемым и запускаем:
```bash
chmod +x ./init-vps.sh
./init-vps.sh
```

**Готово!** Скрипт выведет: `Успешно! Проект развернут и доступен по адресу: https://вашдомен.ru`.

### Обновление приложения в будущем

Если вам необходимо обновить проект (без перевыпуска SSL):

```bash
git pull
docker-compose -f docker-compose.prod.yml up -d --build web
```

### SSL обновляется автоматически

Раз в полдня (или при старте) работает скрытый контейнер `certbot`, который без простоев проверяет необходимость продления SSL-сертификата. Вам ничего делать не нужно.

---

## 🗄️ База данных

В DEV-окружении порт MySQL проброшен наружу как **3308** (чтобы не конфликтовать с локальным MySQL на 3306 и другими вашими ботами на 3307).

### Параметры подключения для СУБД (DBeaver, TablePlus, HeidiSQL и др.):

- **Host:** `127.0.0.1` (или IP сервера)
- **Port:** `3308`
- **Database:** `serp_db` (значение `DB_NAME` из `.env`)
- **User:** `serp_user` (значение `DB_USER` из `.env`)
- **Password:** `serp_password` (значение `DB_PASSWORD` из `.env`)

**Для доступа под ROOT:**

- **User:** `root`
- **Password:** `root` (значение `MYSQL_ROOT_PASSWORD` из `.env`)

### Резервное копирование

```bash
# Создать бэкап
docker exec serp_db mysqldump -u root -p${MYSQL_ROOT_PASSWORD} ${DB_NAME} > backup.sql

# Восстановить из бэкапа
docker exec -i serp_db mysql -u root -p${MYSQL_ROOT_PASSWORD} ${DB_NAME} < backup.sql
```

### Для пользователей HeidiSQL:
1. **Экспорт:** В старой базе: Правой кнопкой на базу -> "Export database as SQL". Настройки: `Tables: Create`, `Data: Insert`. Сохраните в `.sql`.
2. **Импорт:** Подключитесь к **новому** MySQL (127.0.0.1:3308). 
   *   Вариант А: Меню **File** -> **Run SQL file...** (или клавиша **F9**). Выберите ваш файл.
   *   Вариант Б: Нажмите на иконку папки ("Open SQL file") на панели инструментов, файл откроется в новой вкладке. Нажмите синюю кнопку **"Run"** (Play).

> [!IMPORTANT]
> **Если возникла ошибка SQL (1044): Access denied to database...**
> Это происходит, потому что в вашем SQL-файле есть команда `CREATE DATABASE test_serp`. Пользователь `serp_admin` имеет права только на базу `serp_db`.
> **Решение:** Откройте файл `.sql` в текстовом редакторе и удалите (или закомментируйте `--`) первые строки:
> ```sql
> -- CREATE DATABASE IF NOT EXISTS `test_serp` ...
> -- USE `test_serp`;
> ```
> After this HeidiSQL will import the tables directly into the open `serp_db` database.

> [!WARNING]
> **Если возникла ошибка SQL (1062): Duplicate entry...**
> Это означает, что в базе уже есть данные (например, созданные приложением при первом запуске), и их ID конфликтуют с данными из дампа.
> **Решение:** Перед импортом нужно очистить таблицы в новой базе. В HeidiSQL:
> 1. Выделите все таблицы в базе `serp_db`.
> 2. Нажмите правой кнопкой -> **"Empty table(s) / Truncate"**.
> 3. После этого запустите импорт файла снова.

---

## 🔍 Диагностика проблем

| Проблема                 | Команда                         |
| ------------------------ | ------------------------------- |
| Контейнер не запускается | `docker compose logs web`       |
| Nginx ошибки             | `docker compose logs nginx`     |
| MySQL не поднялась       | `docker compose logs db`        |
| Статус всех сервисов     | `docker compose ps`             |
| Войти в контейнер        | `docker exec -it serp_web bash` |
| Логи приложения          | `cat logs/gunicorn_error.log`   |
