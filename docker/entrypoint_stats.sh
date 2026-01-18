# #!/usr/bin/env bash
# set -e

# # Cargar .env si existe dentro de /app (opcional)
# if [ -f /app/.env ]; then
#   set -a
#   . /app/.env
#   set +a
# fi

# if [[ -z "$POSTGRES_HOST" ]] || [[ -z "$POSTGRES_PORT" ]]; then
#   echo "Error: POSTGRES_HOST y POSTGRES_PORT deben estar definidos"
#   exit 1
# fi
# echo "Esperando a Postgres en $POSTGRES_HOST:$POSTGRES_PORT..."
# TIMEOUT=60
# ELAPSED=0
# while ! nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
#   sleep 1
#   ELAPSED=$((ELAPSED + 1))
#   if [ $ELAPSED -ge $TIMEOUT ]; then
#     echo "Error: Postgres no disponible después de $TIMEOUT segundos"
#     exit 1
#   fi
# done
# echo "Postgres disponible."

# # Aplicar migraciones
# python manage.py migrate --noinput

# # Iniciar Django (puedes cambiar a gunicorn si es para prod)
# exec python manage.py runserver 0.0.0.0:8030
