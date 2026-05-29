@echo off
title Nettoyage Projet
cls
echo.
echo ============================================================
echo  NETTOYAGE DU PROJET
echo ============================================================
echo.

echo Suppression des anciens dashboards Streamlit...
del /Q dashboard_v2.py 2>nul
del /Q dashboard_v3.py 2>nul
del /Q dashboard_v4.py 2>nul
del /Q dashboard_v5.py 2>nul
del /Q dashboard_v5_lite.py 2>nul
del /Q dashboard_v6.py 2>nul
del /Q dashboard_v7.py 2>nul
del /Q dashboard_v8.py 2>nul
del /Q dashboard_old.py 2>nul
del /Q dashboard_before_corrections.py 2>nul
del /Q dashboard_test.py 2>nul
del /Q dashboard_minimal.py 2>nul
del /Q dashboard_fixed.py 2>nul
del /Q dashboard.py 2>nul
echo OK - Dashboards Streamlit supprimes

echo.
echo Suppression des scripts de reinstallation...
del /Q REINSTALLER_STREAMLIT.bat 2>nul
del /Q REINSTALLER_STREAMLIT_FIXED.bat 2>nul
del /Q REINSTALLER_FINAL.bat 2>nul
del /Q TESTER_STREAMLIT.bat 2>nul
del /Q start_dashboard.bat 2>nul
del /Q start_dashboard.ps1 2>nul
del /Q start.ps1 2>nul
del /Q run.bat 2>nul
del /Q LANCER_DASHBOARD.bat 2>nul
del /Q DESACTIVER_VENV.bat 2>nul
echo OK - Scripts obsoletes supprimes

echo.
echo Suppression de la documentation obsolete...
del /Q DASHBOARD_CONSOLIDATION_AUDIT.md 2>nul
del /Q DASHBOARD_DEMARRAGE.md 2>nul
del /Q DASHBOARD_OUVERT.md 2>nul
del /Q DEMARRAGE_SIMPLE.md 2>nul
del /Q OUVRIR_DASHBOARD.md 2>nul
del /Q PROBLEME_STREAMLIT.md 2>nul
del /Q REINSTALLATION.md 2>nul
del /Q SOLUTION_FINALE.md 2>nul
del /Q SOLUTION_VENV.md 2>nul
del /Q CORRECTIONS_MAJEURES.md 2>nul
del /Q ETAT_ACTUEL.md 2>nul
del /Q ETAT_PROJET_FINAL.md 2>nul
del /Q PHASES_1_8_AUDIT.md 2>nul
del /Q PHASES_1_8_COMPLETE.md 2>nul
del /Q PROJET_FINAL_RECAP.md 2>nul
del /Q RECALIBRATION_COMPLETE.md 2>nul
del /Q RECALIBRATION_PHASE1_COMPLETE.md 2>nul
del /Q COMPLETE_SYSTEM_SUMMARY.md 2>nul
del /Q QUICK_START_GUIDE.md 2>nul
del /Q SYSTEM_AUDIT_REPORT.md 2>nul
del /Q VALIDATION_COMPLETE.md 2>nul
del /Q README_FINAL.md 2>nul
echo OK - Documentation obsolete supprimee

echo.
echo Suppression environnement virtuel venv_clean...
rmdir /S /Q venv_clean 2>nul
echo OK - venv_clean supprime

echo.
echo ============================================================
echo  FICHIERS CONSERVES
echo ============================================================
echo.
echo DASHBOARD:
echo   - app_flask.py (nouveau dashboard Flask)
echo   - templates\dashboard.html
echo.
echo BACKEND:
echo   - app\ (tous les services)
echo   - test_dashboard_loading.py
echo.
echo DOCUMENTATION:
echo   - README_FLASK.md (guide Flask)
echo   - PROBLEME_PYTHON314.md (pourquoi Flask)
echo   - VALIDATION_HISTORIQUE.md (validation signaux)
echo.
echo SCRIPTS:
echo   - LANCER_FLASK.bat (nouveau)
echo   - KILL_ALL.bat
echo   - NETTOYER_PROJET.bat (ce script)
echo.
echo ============================================================
echo  TERMINE
echo ============================================================
echo.
echo Projet nettoye !
echo.
echo Pour lancer le dashboard:
echo   LANCER_FLASK.bat
echo.

pause
