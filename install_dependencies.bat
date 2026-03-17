@echo off
echo Установка зависимостей для приложения SERP Parser...
echo.

REM Проверяем, установлен ли pip
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo.Error: Python или pip не найден в системе.
    echo.Пожалуйста, установите Python и убедитесь, что он добавлен в PATH.
    pause
    exit /b 1
)

echo.Устанавливаем зависимости из файла requirements.txt...
python -m pip install --upgrade pip

REM Сначала пробуем установить mysql-connector-python
echo.Устанавливаем MySQL connector...
python -m pip install mysql-connector-python==8.2.0
if errorlevel 1 (
    echo.Ошибка при установке mysql-connector-python, пробуем альтернативный пакет...
    python -m pip install mysqlclient==2.2.4
)

REM Устанавливаем остальные зависимости
echo.Устанавливаем остальные зависимости...
python -m pip install Flask==2.3.3 python-dotenv==1.0.0 pandas==2.1.4 requests==2.31.0 xmltodict==0.13.0 openpyxl==3.1.2

if errorlevel 1 (
    echo.Error: Произошла ошибка при установке зависимостей.
    pause
    exit /b 1
)

echo.
echo.Зависимости успешно установлены!
echo.Теперь вы можете запустить приложение с помощью команды: python serp.py
echo.
pause