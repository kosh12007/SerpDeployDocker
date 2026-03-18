#!/bin/bash
# ==============================================================================
# Скрипт первоначальной настройки VPS: привязка домена и получение SSL (Certbot)
# ==============================================================================

if ! [ -x "$(command -v docker)" ]; then
  echo 'Ошибка: docker не установлен.' >&2
  exit 1
fi

if ! [ -x "$(command -v docker-compose)" ]; then
  # Пытаемся использовать "docker compose" как плагин
  if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
  else
    echo 'Ошибка: docker-compose не установлен.' >&2
    exit 1
  fi
else
  DOCKER_COMPOSE="docker-compose"
fi

if [ ! -f .env ]; then
  echo "Ошибка: Файл .env не найден. Скопируйте .env.example в .env и заполните его параметры (особенно DOMAIN и LETSENCRYPT_EMAIL)."
  exit 1
fi

set -a
source .env
set +a

if [ -z "$DOMAIN" ] || [ -z "$LETSENCRYPT_EMAIL" ]; then
  echo "Ошибка: В файле .env не заданы DOMAIN или LETSENCRYPT_EMAIL."
  echo "Пожалуйста, откройте .env и укажите эти параметры."
  exit 1
fi

DATA_PATH="./certbot"

if [ -d "$DATA_PATH/conf/live/$DOMAIN" ]; then
  echo ""
  read -p "Сертификаты для $DOMAIN уже существуют. Заменить их новыми? (y/N) " decision
  if [ "$decision" != "Y" ] && [ "$decision" != "y" ]; then
    echo "Запуск сервисов без перевыпуска сертификатов..."
    $DOCKER_COMPOSE -f docker-compose.prod.yml up -d --build
    exit
  fi
fi

echo "### Скачивание рекомендованных настроек TLS ..."
if [ ! -e "$DATA_PATH/conf/options-ssl-nginx.conf" ] || [ ! -e "$DATA_PATH/conf/ssl-dhparams.pem" ]; then
  echo "### Загрузка параметров TLS..."
  mkdir -p "$DATA_PATH/conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nodejs/options-ssl-nginx.conf > "$DATA_PATH/conf/options-ssl-nginx.conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$DATA_PATH/conf/ssl-dhparams.pem"
fi

echo "### Создание временного SSL сертификата для $DOMAIN ..."
mkdir -p "$DATA_PATH/conf/live/$DOMAIN"
mkdir -p "$DATA_PATH/www"
$DOCKER_COMPOSE -f docker-compose.prod.yml run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout '/etc/letsencrypt/live/$DOMAIN/privkey.pem' \
    -out '/etc/letsencrypt/live/$DOMAIN/fullchain.pem' \
    -subj '/CN=localhost'" certbot

echo "### Запуск Nginx ..."
$DOCKER_COMPOSE -f docker-compose.prod.yml up --force-recreate -d nginx

echo "### Удаление временного сертификата ..."
$DOCKER_COMPOSE -f docker-compose.prod.yml run --rm --entrypoint "\
  rm -Rf /etc/letsencrypt/live/$DOMAIN && \
  rm -Rf /etc/letsencrypt/archive/$DOMAIN && \
  rm -Rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot

echo "### Запрос SSL сертификата у Let's Encrypt ..."
# Включаем staging режим если нужно для тестов, чтобы не забанили
# Чтобы снять ограничение, просто ничего не передаём
$DOCKER_COMPOSE -f docker-compose.prod.yml run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    --email $LETSENCRYPT_EMAIL \
    --agree-tos --no-eff-email \
    --force-renewal \
    -d $DOMAIN -d www.$DOMAIN" certbot

echo "### Перезапуск Nginx для применения новых сертификатов ..."
$DOCKER_COMPOSE -f docker-compose.prod.yml exec nginx nginx -s reload

echo "### Включение веб-приложения и БД ..."
$DOCKER_COMPOSE -f docker-compose.prod.yml up -d --build web db

echo ""
echo "=========================================================="
echo "Успешно! Проект развернут и доступен по адресу: https://$DOMAIN"
echo "=========================================================="
