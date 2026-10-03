@echo off
rem Flowlytics en un paso (Windows): entorno, base con las camaras de ejemplo,
rem analisis de todas las camaras y el panel en http://localhost:8010/
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo Primera vez: creando el entorno e instalando dependencias ^(unos minutos^)...
  py -3 -m venv .venv 2>nul || python -m venv .venv
  .venv\Scripts\python.exe -m pip install -q --upgrade pip
  .venv\Scripts\python.exe -m pip install -q -r requirements.txt
)

set SIN_CUENTA=1
set DJANGO_DEBUG=True
if not defined DETECTOR_IMGSZ set DETECTOR_IMGSZ=640
.venv\Scripts\python.exe manage.py migrate --noinput -v 0
rem Solo la primera vez: las 6 camaras de ejemplo (3 videos + 3 en vivo de YouTube).
.venv\Scripts\python.exe manage.py shell -c "from cameras.models import Camera; raise SystemExit(0 if Camera.objects.exists() else 1)" || .venv\Scripts\python.exe manage.py loaddata demo\camaras_demo.json

if not exist logs mkdir logs
rem Un solo proceso mantiene vivas todas las camaras; si una se cae, la relanza.
rem En esta misma ventana (no en otra minimizada): cerrar esa ventana mataba todas las camaras.
set PYTHONUNBUFFERED=1
start "" /b cmd /c ".venv\Scripts\python.exe manage.py correr_camaras >> logs\supervisor.log 2>&1"
start "" /b cmd /c "timeout /t 4 >nul & start http://localhost:8010/"
echo Panel en http://localhost:8010/  -  cierra esta ventana para parar todo (panel y camaras)
.venv\Scripts\python.exe manage.py runserver 8010
