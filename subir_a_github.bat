@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================================
echo   Subir Workspace ChatGPT a GitHub (Monorepo)
echo ========================================================
echo.

set REPO_URL=%1
if "%REPO_URL%"=="" (
    set /p REPO_URL="Pega la URL del repositorio de GitHub (ej: https://github.com/FakeCxbas/workspace-chatgpt.git): "
)

if "%REPO_URL%"=="" (
    echo [ERROR] No ingresaste ninguna URL.
    pause
    exit /b 1
)

echo.
echo [1/3] Configurando repositorio remoto...
git remote remove origin 2>nul
git remote add origin %REPO_URL%
if errorlevel 1 (
    echo [ERROR] No se pudo agregar el remoto. Revisa la URL.
    pause
    exit /b 1
)

echo [2/3] Asegurando rama principal en 'main'...
git branch -M main

echo [3/3] Subiendo ramas y commits a GitHub...
git push -u origin main
if errorlevel 1 (
    echo.
    echo [ERROR] Ocurrio un problema al hacer push.
    echo Asegurate de haber creado el repositorio vacio en GitHub previamente.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   ¡Subida completada con exito!
echo   Para clonar en tu otra PC usa:
echo   git clone %REPO_URL% ChatGPT
echo ========================================================
pause
