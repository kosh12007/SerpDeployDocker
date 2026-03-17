@echo off
setlocal EnableDelayedExpansion

:: Получаем текущую дату и время
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set YYYY=%datetime:~0,4%
set MM=%datetime:~4,2%
set DD=%datetime:~6,2%
set HH=%datetime:~8,2%
set MIN=%datetime:~10,2%
set SS=%datetime:~12,2%

:: Формируем имя архива
set "ARCHIVE_NAME=project_backup_%YYYY%-%MM%-%DD%_%HH%-%MIN%-%SS%.zip"

:: Создаем временную директорию для сбора файлов
set TEMP_DIR=temp_backup_%YYYY%-%MM%-%DD%_%HH%-%MIN%-%SS%
mkdir %TEMP_DIR%

echo Creating backup...

:: Копируем нужные папки
echo Copying directories...
xcopy /E /I /Q /Y app "%TEMP_DIR%\app"
xcopy /E /I /Q /Y static "%TEMP_DIR%\static"
xcopy /E /I /Q /Y templates "%TEMP_DIR%\templates"
xcopy /E /I /Q /Y docs "%TEMP_DIR%\docs"
xcopy /E /I /Q /Y migrations "%TEMP_DIR%\migrations"

:: Копируем нужные файлы из корня
echo Copying root files...
copy *.py "%TEMP_DIR%\"
copy *.bat "%TEMP_DIR%\"
copy *.js "%TEMP_DIR%\"
copy *.html "%TEMP_DIR%\"
copy *.css "%TEMP_DIR%\"
copy *.env "%TEMP_DIR%\"
copy *.json "%TEMP_DIR%\"
@REM copy *.sql "%TEMP_DIR%\"
copy requirements.txt "%TEMP_DIR%\"

:: Создаем архив
echo Creating archive...
powershell Compress-Archive -Path "%TEMP_DIR%\*" -DestinationPath "%ARCHIVE_NAME%" -Force

:: Удаляем временную директорию
echo Cleaning up...
rmdir /S /Q %TEMP_DIR%

echo Backup created successfully: %ARCHIVE_NAME%
echo.
pause