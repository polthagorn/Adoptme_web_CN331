#!/usr/bin/env bash
set -o errexit   # Exit immediately if a command fails

echo "Starting build process"

echo "🔹 Upgrading pip"
pip install --upgrade pip

echo "🔹 Installing dependencies"
pip install -r requirements.txt

echo "🔹 Collecting static files"
python manage.py collectstatic --no-input

echo "🔹 Applying database migrations"
python manage.py migrate

echo "🔹 Ensuring default superuser exists"
python manage.py shell << EOF
import os
from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get("ADMIN_USERNAME", "admin")
email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
password = os.environ.get("ADMIN_PASSWORD", "changeme123")

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created successfully.")
else:
    print(f"Superuser '{username}' already exists.")
EOF

echo "Build completed "
