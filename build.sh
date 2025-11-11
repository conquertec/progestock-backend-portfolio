#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Setup Site object for django.contrib.sites
python manage.py setup_site

# Create superuser if environment variables are set (optional)
python manage.py create_admin

# Collect static files (if needed for production)
python manage.py collectstatic --no-input
