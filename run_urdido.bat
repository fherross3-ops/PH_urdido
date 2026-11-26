@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

REM ============================================================
REM CONFIGURACION
REM ============================================================
set "BASE_DIR=F:\APP_Mini_JTX\APP_Urdido\King_extractor_PH_Urdido\PH-Sisgo-Extractor-Urdido\Extr_01-Sisgo-Urdido"
set "REPO_DIR=%BASE_DIR%\PH_urdido-main"
set "URL_DASHBOARD=https://TU-DASHBOARD.netlify.app"

REM ============================================================
REM CALCULAR FECHA DE AYER (YYYYMMDD)
REM ============================================================
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).AddDays(-1).ToString('yyyyMMdd')"') do set "AYER=%%i"

echo ============================================================
echo   ACTUALIZACION URDIDO - %AYER%
echo ============================================================
echo.

REM ============================================================
REM PASO 1: EXTRACTOR (sitio SISGO)
REM ============================================================
echo [1/4] Extrayendo del sitio SISGO...
cd /d "%BASE_DIR%"
python Inc_F_extractor_urdido_backup.py --inicio %AYER% --fin %AYER%
if errorlevel 1 (
    echo [ERROR] Fallo el extractor. Abortando.
    pause
    exit /b 1
)
echo [OK] Extractor completado.
echo.

REM ============================================================
REM PASO 2: APLANAR PDFs
REM ============================================================
echo [2/4] Aplanando PDFs...
cd /d "%BASE_DIR%"
python automatico_extraePDF.py
if errorlevel 1 (
    echo [ERROR] Fallo al aplanar PDFs. Abortando.
    pause
    exit /b 1
)
echo [OK] PDFs aplanados.
echo.

REM ============================================================
REM PASO 3: CONVERTIDOR
REM ============================================================
echo [3/4] Generando CSVs...
cd /d "%BASE_DIR%"
python extraer_csv_pdf_urdido.py
if errorlevel 1 (
    echo [ERROR] Fallo el convertidor. Abortando.
    pause
    exit /b 1
)
echo [OK] CSVs generados.
echo.

REM ============================================================
REM VERIFICAR QUE EXISTEN LOS 3 CSV
REM ============================================================
set "FALTA=0"
if not exist "%BASE_DIR%\data\produccion_%AYER%.csv"       (echo [ERROR] Falta produccion_%AYER%.csv & set "FALTA=1")
if not exist "%BASE_DIR%\data\roturas_%AYER%.csv"          (echo [ERROR] Falta roturas_%AYER%.csv & set "FALTA=1")
if not exist "%BASE_DIR%\data\tiempos_perdidos_%AYER%.csv" (echo [ERROR] Falta tiempos_perdidos_%AYER%.csv & set "FALTA=1")
if "%FALTA%"=="1" (
    echo [ERROR] Faltan CSVs. Abortando.
    pause
    exit /b 1
)

REM ============================================================
REM PASO 4: COPIAR A REPO Y PUSH
REM ============================================================
echo [4/4] Copiando CSVs al repo y subiendo a GitHub...

if not exist "%REPO_DIR%\data" (
    echo [ERROR] No existe %REPO_DIR%\data
    pause
    exit /b 1
)

copy /Y "%BASE_DIR%\data\produccion_%AYER%.csv"         "%REPO_DIR%\data\" >nul
copy /Y "%BASE_DIR%\data\roturas_%AYER%.csv"            "%REPO_DIR%\data\" >nul
copy /Y "%BASE_DIR%\data\tiempos_perdidos_%AYER%.csv"   "%REPO_DIR%\data\" >nul

cd /d "%REPO_DIR%"
git add "data/produccion_%AYER%.csv" "data/roturas_%AYER%.csv" "data/tiempos_perdidos_%AYER%.csv"
git commit -m "Datos Urdido %AYER%"
git push
if errorlevel 1 (
    echo [ERROR] Fallo el push a GitHub. Abortando.
    pause
    exit /b 1
)
echo [OK] Push completado.
echo.

REM ============================================================
REM ABRIR DASHBOARD
REM ============================================================
echo Abriendo dashboard...
start "" "%URL_DASHBOARD%"

echo.
echo ============================================================
echo   PROCESO COMPLETADO - %AYER%
echo ============================================================
pause