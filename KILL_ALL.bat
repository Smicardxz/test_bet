@echo off
title Kill All Streamlit
cls
echo.
echo ============================================================
echo  ARRET DE TOUS LES PROCESSUS STREAMLIT
echo ============================================================
echo.

echo Arret des processus streamlit...
taskkill /F /IM streamlit.exe 2>nul
if %errorlevel% equ 0 (
    echo OK - Processus streamlit arretes
) else (
    echo Aucun processus streamlit trouve
)

echo.
echo Arret des processus python (streamlit)...
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr "PID"') do (
    taskkill /F /PID %%a 2>nul
)

echo.
echo ============================================================
echo  TERMINE
echo ============================================================
echo.
echo Tous les processus ont ete arretes.
echo Vous pouvez maintenant relancer le dashboard.
echo.

pause
