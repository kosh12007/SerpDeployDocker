# Развёртывание в Docker

## Структура файлов

```
├── Dockerfile                    # Образ Flask-приложения
├── docker-compose.yml            # DEV: http://localhost
├── docker-compose.prod.yml       # PROD: https://seoorbita.ru
├── .env.example                  # Шаблон переменных (скопировать в .env)
├── .dockerignore                 # Исключения для образа
└── docker/
    ├── entrypoint.sh             # Старт: ждёт MySQL → gunicorn
    └── nginx/
        ├── nginx.dev.conf        # Nginx для DEV (HTTP)
        └── nginx.prod.conf       # Nginx для PROD (HTTPS)
```

---

## 🖥️ DEV — локальная разработка

### Требования

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Шаг 1: Создать `.env`

```bash
cp .env.example .env
```

Заполнить в `.env`:

- `DB_PASSWORD` — любой пароль для MySQL
- `MYSQL_ROOT_PASSWORD` — root-пароль MySQL
- `SECRET_KEY` — сгенерировать: `python -c "import secrets; print(secrets.token_hex(24))"`
- `API_KEY` — ключ XMLRiver

### Шаг 2: Запустить

```bash
docker compose up -d --build
```

### Шаг 3: Открыть

```
http://localhost
```

### Полезные команды

```bash
# Посмотреть логи
docker compose logs -f web
docker compose logs -f nginx

# Остановить
docker compose down

# Остановить и удалить данные БД
docker compose down -v

# Перезапустить только web
docker compose restart web
```

---

## 🌐 PROD — сервер seoorbita.ru

### Требования

- VPS/сервер с Ubuntu 22.04
- Docker + Docker Compose installed
- DNS запись A: `seoorbita.ru` → IP сервера

### Шаг 1: Скопировать проект на сервер

```bash
scp -r ./serp_docker user@server:/srv/serp
# или через git clone
```

### Шаг 2: Создать `.env`

```bash
cd /srv/serp
cp .env.example .env
nano .env  # заполнить секреты
```

В `.env` также установить:

```
MODE=hosting
```

### Шаг 3: Получить SSL-сертификат (первый раз)

> ⚠️ Nginx сначала запускается в HTTP-режиме для верификации домена

```bash
# 1. Создать директории для Certbot
mkdir -p certbot/conf certbot/www

# 2. Запустить nginx (временно, только HTTP)
# В nginx.prod.conf временно закомментировать весь HTTPS-блок (server 443)
# и в HTTP-блоке убрать redirect, добавить вместо него proxy_pass

# 3. Получить сертификат
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email admin@seoorbita.ru \
  --agree-tos \
  --no-eff-email \
  -d seoorbita.ru \
  -d www.seoorbita.ru

# 4. Убедиться что сертификаты созданы
ls certbot/conf/live/seoorbita.ru/
```

### Шаг 4: Запустить всё

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### Шаг 5: Проверить

```bash
curl -I https://seoorbita.ru/
# Ожидается: HTTP/2 200 или 302
```

### Обновление приложения

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build web
```

### SSL обновляется автоматически

Certbot-сервис в контейнере проверяет и обновляет сертификат каждые 12 часов.

---

## 🗄️ База данных

В DEV-окружении порт MySQL проброшен наружу как **3307** (чтобы не конфликтовать с локальным MySQL на 3306).

### Параметры подключения для СУБД (DBeaver, TablePlus и др.):

- **Host:** `127.0.0.1`
- **Port:** `3307`
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
2. **Импорт:** Подключитесь к **новому** MySQL (127.0.0.1:3307). 
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
