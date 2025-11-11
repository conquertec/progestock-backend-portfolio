#!/usr/bin/env bash
# Start the Gunicorn server
# Render provides the PORT environment variable

gunicorn progestock_backend.wsgi:application \
    --bind 0.0.0.0:${PORT:-10000} \
    --workers 4 \
    --threads 2 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
