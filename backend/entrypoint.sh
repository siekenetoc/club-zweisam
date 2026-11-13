#!/bin/sh
set -e

cd /app

if [ "${DJANGO_SETTINGS_MODULE:-}" != "clubzweisam.settings.dev" ]; then
    python manage.py collectstatic --noinput
fi

python manage.py migrate --noinput

exec "$@"
