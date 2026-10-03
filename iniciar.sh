#!/usr/bin/env bash
# Flowlytics en un paso (Mac/Linux): entorno, base con las camaras de ejemplo,
# analisis de todas las camaras y el panel en http://localhost:8010/
set -e
cd "$(dirname "$0")"

PY=${PYTHON:-python3}
if [ ! -x .venv/bin/python ]; then
  echo "Primera vez: creando el entorno e instalando dependencias (unos minutos)..."
  "$PY" -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
fi

export PYTHONUNBUFFERED=1 SIN_CUENTA=1 DJANGO_DEBUG=True DETECTOR_IMGSZ=${DETECTOR_IMGSZ:-640}
.venv/bin/python manage.py migrate --noinput -v 0
# Solo la primera vez: las 6 camaras de ejemplo (3 videos + 3 en vivo de YouTube).
.venv/bin/python manage.py shell -c "from cameras.models import Camera; raise SystemExit(0 if Camera.objects.exists() else 1)" \
  || .venv/bin/python manage.py loaddata demo/camaras_demo.json

mkdir -p logs
.venv/bin/python manage.py correr_camaras >> logs/supervisor.log 2>&1 &
CAMARAS=$!
trap 'kill $CAMARAS 2>/dev/null' EXIT

( sleep 4; (command -v xdg-open >/dev/null && xdg-open http://localhost:8010/) || open http://localhost:8010/ ) >/dev/null 2>&1 &
echo "Panel en http://localhost:8010/  (Ctrl-C para parar todo)"
.venv/bin/python manage.py runserver 8010
