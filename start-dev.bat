@echo off
title LuluSchools - Dev Server

echo.
echo  LuluSchools - Demarrage de l environnement de dev
echo.

set BACKEND=D:\MES PROJETS\IA\LuluSchool\backend
set FRONTEND=D:\MES PROJETS\IA\LuluSchool\frontend
set PYTHON=D:\MES PROJETS\IA\LuluSchool\backend\.venv\Scripts\python.exe

if not exist "%PYTHON%" (
  echo [ERREUR] Python introuvable : %PYTHON%
  pause
  exit /b 1
)

echo [1/3] Demarrage du backend FastAPI...
echo @echo off > "%TEMP%\lulu_b.bat"
echo cd /d "D:\MES PROJETS\IA\LuluSchool\backend" >> "%TEMP%\lulu_b.bat"
echo "D:\MES PROJETS\IA\LuluSchool\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload >> "%TEMP%\lulu_b.bat"
echo pause >> "%TEMP%\lulu_b.bat"
start "Backend" cmd /k "%TEMP%\lulu_b.bat"
ping -n 6 127.0.0.1 >nul

echo [2/3] Demarrage de ngrok...
start "ngrok" cmd /k "ngrok http 8000"
ping -n 4 127.0.0.1 >nul

echo [3/3] Demarrage du frontend Vite...
echo @echo off > "%TEMP%\lulu_f.bat"
echo cd /d "D:\MES PROJETS\IA\LuluSchool\frontend" >> "%TEMP%\lulu_f.bat"
echo npm run dev >> "%TEMP%\lulu_f.bat"
echo pause >> "%TEMP%\lulu_f.bat"
start "Frontend" cmd /k "%TEMP%\lulu_f.bat"

echo.
echo  OK - Serveurs demarres !
echo  Frontend : http://localhost:5173
echo  Backend  : http://localhost:8000
echo  API Docs : http://localhost:8000/docs
echo  ngrok    : http://127.0.0.1:4040
echo.
echo  Fermez les 3 fenetres CMD pour tout arreter.
echo.
pause