# optionsTrader

Monorepo for a custom options trading platform.

## Structure
- `backend/` — Django project (`config/` settings, apps: `portfolio/`, `strategies/`, `backtests/`, `accounts/`)
- `ui/` — React/Next.js frontend (to be added)

## Dev quickstart (backend)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install django djangorestframework django-environ psycopg2-binary ib-insync pydantic
python manage.py migrate
python manage.py runserver
