# Шпаргалка по командам Docker (Serp)

Здесь собраны все основные команды для управления контейнерами проекта в двух вариантах:
1. **Базовый (DEV / по IP)** — без домена и SSL, работает по протоколу HTTP (порт 80).
2. **Продакшн (PROD / с доменом)** — с привязанным доменом и автоматическим HTTPS (SSL от Let's Encrypt).

---

## 📥 Первоначальное скачивание (Клонирование)
Команда для того, чтобы впервые скачать проект из репозитория GitHub/GitLab на ваш сервер:
```bash
git clone https://github.com/ВАШ_ПОЛЬЗОВАТЕЛЬ/ВАШ_РЕПОЗИТОРИЙ.git
cd ИМЯ_ПАПКИ_ПРОЕКТА
```
*(Не забудьте подставить вашу реальную ссылку на репозиторий)*

---

## Вариант 1: Базовый (DEV / запуск по IP)
*Использует стандартный конфигурационный файл `docker-compose.yml`.*

### 🚀 Запуск и сборка
Запустить все контейнеры в фоновом режиме (пересоберет образы, если есть изменения в коде):
```bash
docker-compose up -d --build
```

### 🛑 Остановка
Остановить все контейнеры (без удаления данных БД):
```bash
docker-compose down
```

### ♻️ Перезапуск
Перезапустить **все** контейнеры:
```bash
docker-compose restart
```
Перезапустить **только веб-приложение** (Flask/Python), например, после изменения кода:
```bash
docker-compose restart web
```

### 📝 Логи
Смотреть логи всех контейнеров в реальном времени:
```bash
docker-compose logs -f
```
Смотреть логи конкретного контейнера (например, если есть ошибки в Python коде):
```bash
docker-compose logs -f web
```
*(Для выхода из логов нажмите `Ctrl + C`)*

### ⚠️ Полное удаление (Сброс)
Остановить контейнеры и **ПОЛНОСТЬЮ удалить базу данных** и все тома:
```bash
docker-compose down -v
```

---

## Вариант 2: Продакшн (PROD / с доменом и HTTPS)
*Использует конфигурационный файл `docker-compose.prod.yml`. В командах обязательно добавлять флаг `-f docker-compose.prod.yml`.*

### ✨ Первоначальный запуск (получение SSL)
Запускается **только один раз** при первом деплое или смене домена в `.env`:
```bash
./init-vps.sh
```

### 🚀 Обычный запуск и сборка (после обновления кода)
Если вы скачали обновления (например, через `git pull`), пересобирите и запустите:
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```
Обновить **только Python-приложение**, не трогая Nginx и базу данных:
```bash
docker-compose -f docker-compose.prod.yml up -d --build web
```

### 🛑 Остановка
Остановить проект:
```bash
docker-compose -f docker-compose.prod.yml down
```

### ♻️ Перезапуск
Перезапустить **все** контейнеры:
```bash
docker-compose -f docker-compose.prod.yml restart
```
Перезапустить **только веб-приложение** (часто используется после мелких правок):
```bash
docker-compose -f docker-compose.prod.yml restart web
```
Перезапустить **только Nginx** (если поменяли что-то в конфигах веб-сервера):
```bash
docker-compose -f docker-compose.prod.yml restart nginx
```

### 📝 Логи
Смотреть общие логи продакшна:
```bash
docker-compose -f docker-compose.prod.yml logs -f
```
Логи Nginx (полезно при ошибках 502 Bad Gateway):
```bash
docker-compose -f docker-compose.prod.yml logs -f nginx
```
Логи приложения (Flask):
```bash
docker-compose -f docker-compose.prod.yml logs -f web
```

### 🔒 Сертификаты (Let's Encrypt)
Сертификаты обновляются автоматически каждые 12 часов. 
Если вам нужно **принудительно** обновить сертификат вручную прямо сейчас:
```bash
docker-compose -f docker-compose.prod.yml run --rm certbot renew
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

---

## 🛠 Общие полезные команды (для обоих вариантов)

**Как зайти внутрь контейнера (например, чтобы проверить файлы в Linux):**
```bash
# Базовый вариант
docker-compose exec web bash

# Продакшн вариант
docker-compose -f docker-compose.prod.yml exec web bash
```

**Проверка статуса контейнеров (что работает, а что упало):**
```bash
docker ps
```
