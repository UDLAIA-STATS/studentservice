#!/usr/bin/env bash
set -e

# Cargar .env si existe dentro de /app (opcional)
if [ -f /app/.env ]; then
  set -a
  . /app/.env
  set +a
fi


# Aplicar migraciones
python manage.py migrate --noinput

# Iniciar Django (puedes cambiar a gunicorn si es para prod)
exec python manage.py runserver 0.0.0.0:8030
