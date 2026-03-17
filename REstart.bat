@echo off
echo ==========================================
echo  Перезапуск проекта Serp (Docker)
echo ==========================================
echo.

echo Останавливаем контейнеры...
docker compose down

echo.
echo Запускаем контейнеры...
docker compose up -d

if %errorlevel% neq 0 (
    echo [ERROR] Ошибка при перезапуске docker compose!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  Проект Serp перезапущен!
echo ==========================================
echo.
echo URL:      http://localhost
echo.
echo Для просмотра логов: docker compose logs -f web
echo Для остановки:       docker compose down
echo.
pause
