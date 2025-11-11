#!/bin/bash
set -e

echo "Starting ProGestock Backend..."

# Debug: Print database-related environment variables
echo "=== DEBUG: Database Environment Variables ==="
echo "DATABASE_URL: ${DATABASE_URL:-NOT SET}"
echo "DATABASE_PRIVATE_URL: ${DATABASE_PRIVATE_URL:-NOT SET}"
echo "DATABASE_PUBLIC_URL: ${DATABASE_PUBLIC_URL:-NOT SET}"
echo "PGHOST: ${PGHOST:-NOT SET}"
echo "PGPORT: ${PGPORT:-NOT SET}"
echo "PGUSER: ${PGUSER:-NOT SET}"
echo "PGDATABASE: ${PGDATABASE:-NOT SET}"
echo "PGPASSWORD: ${PGPASSWORD:+SET (hidden)}"
echo "============================================="

# If DATABASE_URL is not set but we have individual Postgres variables, construct it
if [ -z "$DATABASE_URL" ] && [ -n "$PGHOST" ] && [ -n "$PGUSER" ] && [ -n "$PGPASSWORD" ] && [ -n "$PGDATABASE" ]; then
    export DATABASE_URL="postgresql://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT:-5432}/${PGDATABASE}"
    echo "Constructed DATABASE_URL from individual Postgres variables"
elif [ -n "$DATABASE_PRIVATE_URL" ]; then
    export DATABASE_URL="$DATABASE_PRIVATE_URL"
    echo "Using DATABASE_PRIVATE_URL as DATABASE_URL"
elif [ -n "$DATABASE_PUBLIC_URL" ]; then
    export DATABASE_URL="$DATABASE_PUBLIC_URL"
    echo "Using DATABASE_PUBLIC_URL as DATABASE_URL"
fi

# Compile translation messages
echo "Compiling translation messages..."
python manage.py compilemessages --ignore=venv --ignore=env 2>&1 || echo "Note: compilemessages completed with warnings (this is usually safe to ignore)"

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Setup Site object
echo "Setting up Site object..."
python manage.py setup_site

# Create superuser if environment variables are set
echo "Creating superuser (if configured)..."
python manage.py create_admin

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Gunicorn
echo "Starting Gunicorn server..."
exec gunicorn progestock_backend.wsgi:application \
    --bind 0.0.0.0:${PORT:-10000} \
    --workers 4 \
    --threads 2 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
