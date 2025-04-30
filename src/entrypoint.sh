set -e

echo "→ Применяем миграции…"
poetry run manage.py makemigrations --noinput
poetry run python manage.py migrate --noinput

echo "→ Собираем статику…"
poetry run python manage.py collectstatic --noinput
exec "$@"
