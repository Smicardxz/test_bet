@echo off
title Dashboard Flask
cls
echo.
echo ============================================================
echo  DASHBOARD FLASK
echo ============================================================
echo.

echo Installation de Flask (si necessaire)...
python -m pip install flask --quiet
echo.

echo Demarrage du dashboard...
echo.
echo ============================================================
echo  DASHBOARD ACTIF
echo ============================================================
echo.
echo URL: http://localhost:5000
echo.
echo Le navigateur devrait s'ouvrir automatiquement.
echo Si ce n'est pas le cas, ouvrez: http://localhost:5000
echo.
echo Pour arreter: Fermez cette fenetre ou Ctrl+C
echo.
echo ============================================================
echo.

REM Ouvrir le navigateur après 3 secondes
start /B timeout /t 3 /nobreak >nul && start http://localhost:5000

REM Lancer Flask
python app_flask.py

pause
