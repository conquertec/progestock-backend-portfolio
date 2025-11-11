web: python manage.py migrate --no-input && gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
release: python manage.py migrate --no-input
