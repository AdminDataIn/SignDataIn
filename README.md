# DataIn Signature App

Proyecto Django standalone para ejecutar `signature_service` como producto independiente.

## Ejecucion local

```bash
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

UI:

- `http://127.0.0.1:8000/signatures/`

API:

- `http://127.0.0.1:8000/api/signatures/`
- `http://127.0.0.1:8000/api/webhooks/signatures/`

Health:

- `http://127.0.0.1:8000/health/`
