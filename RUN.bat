@echo off
setlocal
cd /d "%~dp0"
set "PDF_ARG=%~1"
set "APP_PATH="

if exist "dist\BDC Generator\BDC Generator.exe" (
    set "APP_PATH=%~dp0dist\BDC Generator\BDC Generator.exe"
) else if exist "BDC Generator.exe" (
    set "APP_PATH=%~dp0BDC Generator.exe"
)

if defined APP_PATH (
    if "%PDF_ARG%"=="" (
        start "" "%APP_PATH%"
    ) else (
        start "" "%APP_PATH%" "%PDF_ARG%"
    )
) else (
    if "%PDF_ARG%"=="" (
        python main.py
    ) else (
        python main.py "%PDF_ARG%"
    )
)

endlocal
