@echo off
echo ==========================================
echo  Запуск проекта Serp (Docker)
echo ==========================================
echo.

REM Проверка Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker не найден! Установите Docker Desktop.
    pause
    exit /b 1
)

echo [OK] Docker найден
echo.

REM Проверка наличия .env
if not exist .env (
    echo [ERROR] Файл .env не найден!
    echo Создайте файл .env на основе шаблона .env.example.
    pause
    exit /b 1
)

echo [OK] .env найден
echo.

REM Запуск docker compose
echo Запуск контейнеров...
docker compose up -d

if %errorlevel% neq 0 (
    echo [ERROR] Ошибка при запуске docker compose!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  Проект Serp запущен!
echo ==========================================
echo.
echo URL:      http://localhost
echo.
echo Для просмотра логов: docker compose logs -f web
echo Для остановки:       docker compose down
echo.
pause
