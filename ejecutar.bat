@echo off
title Pipeline Urdido - Automatizacion Completa
color 0A
echo ============================================================
echo  INICIANDO PROCESO AUTOMATICO (EXTRACCION + CONVERSION + GIT)
echo ============================================================
echo.

echo [PASO 1/3] Ejecutando extraccion y conversion de datos...
python pipeline_unificado.py

if errorlevel 1 (
    echo.
    echo ❌ ERROR: El script de Python fallo. No se hara el push a Git.
    echo Revisa los mensajes de error arriba.
    pause
    exit /b 1
)

echo.
echo [PASO 2/3] Preparando solo la carpeta 'data' para Git...
git add data/

echo.
echo [PASO 3/3] Sincronizando y subiendo a GitHub (Netlify se actualizara)...

REM 1. Hacemos el commit de los cambios locales
git commit -m "Actualizacion automatica %date% %time%"

REM 2. Traemos cualquier cambio remoto y combinamos (Evita errores de divergencia)
git pull --rebase origin main

REM 3. Subimos todo a GitHub
git push origin main

if errorlevel 1 (
    echo.
    echo ❌ ERROR: Fallo la sincronizacion. Revisa tu conexion o token de GitHub.
) else (
    echo.
    echo ============================================================
    echo  ✨ ¡EXITO TOTAL!
    echo  Los datos estan en GitHub y Netlify se esta actualizando.
    echo ============================================================
)

echo.
echo Presiona cualquier tecla para salir.
pause >nul