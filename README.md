# APED Enterprise Monitoring & Management

A responsive Django application built around the eight sheets in **APED Monitoring Forms.xlsx**. It provides configurable monitoring forms, field visit records, attendance registers, follow-up actions, searchable/filterable records, Excel/PDF exports, dashboard summaries, authentication, and an admin interface.

## Included monitoring modules
- Farmer group / seed growing monitoring
- Pig monitoring
- Goat monitoring
- Beekeeping / apiary monitoring
- Peacebuilding: dialogue sessions, conflict incidents, training feedback, mediation cases, impact monitoring
- Field visit attendance sheet with gender, age, disability and contact fields

VSLA is a standalone module under `/vsla/`. Its record workflow is separate from the general monitoring catalog and is seeded through the normal database migrations.

The workbook's structured fields are represented as configurable sections and questions. Repeating tables (such as livestock distribution, crop monitoring and attendance) can be recorded as repeatable rows in the record's structured data. This avoids forcing field staff to use unwieldy fixed-width forms while retaining all source-tool prompts.

## Setup
Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_monitoring_forms
python manage.py createsuperuser
python manage.py runserver
```
Visit http://127.0.0.1:8000/ and sign in. The first user can be created with `createsuperuser`.
Copy `.env.example` to `.env` for local configuration. SQLite is used by default for development; production should set `DATABASE_URL` to PostgreSQL, `DJANGO_DEBUG=False`, a strong `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and `DJANGO_CSRF_TRUSTED_ORIGINS`.

For a production web process, use `gunicorn aped_config.wsgi:application` (also provided in `Procfile`). Run `python manage.py collectstatic --noinput` during deployment, and run migrations before serving traffic.

The form seeder accepts a workbook path: `python manage.py seed_monitoring_forms path/to/APED Monitoring Forms.xlsx`.

## Security and deployment notes
- Login is required to view operational data.
- CSRF protection, Django password hashing, session authentication and permission-aware Django admin are enabled.
- Use HTTPS, strong credentials, regular backups and least-privilege staff accounts in production.
- The starter project is intentionally self-contained; review data retention, consent, safeguarding and access rules with APED before deploying sensitive case data.
