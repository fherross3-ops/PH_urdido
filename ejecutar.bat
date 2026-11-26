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
    echo ERROR: El script de Python fallo. No se hara el push a Git.
    pause
    exit /b 1
)

echo.
echo [PASO 2/3] Preparando archivos para Git...
git add data/

echo.
echo [PASO 3/3] Subiendo a GitHub (Netlify se actualizara automaticamente)...
git commit -m "Actualizacion automatica %date% %time%"
git push origin main

if errorlevel 1 (
    echo.
    echo ERROR: Fallo el push. Revisa tu conexion o token.
) else (
    echo.
    echo ============================================================
    echo  EXITO TOTAL! Datos en GitHub y Netlify actualizandose.
    echo ============================================================
)

echo.
echo Presiona cualquier tecla para salir.
pause >nul