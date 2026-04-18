# Despliegue en VPS Ubuntu

## Objetivo

Desplegar la app Django de firma como producto independiente en un VPS y publicarla bajo un subdominio como:

- `sign.datain.pro`
- `app.datain.pro`

WordPress sigue aparte. Este proyecto corre por separado con Django + Gunicorn + Nginx + PostgreSQL.

## 1. Preparar servidor

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx postgresql postgresql-contrib
```

## 2. Crear base de datos PostgreSQL

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE signature_service;
CREATE USER signature_user WITH PASSWORD 'strong-password';
ALTER ROLE signature_user SET client_encoding TO 'utf8';
ALTER ROLE signature_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE signature_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE signature_service TO signature_user;
\q
```

## 3. Publicar código

```bash
sudo mkdir -p /var/www/signature_service
sudo chown $USER:$USER /var/www/signature_service
```

Copia el proyecto a `/var/www/signature_service`.

## 4. Crear entorno virtual e instalar dependencias

```bash
cd /var/www/signature_service
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Configurar variables de entorno

```bash
cp .env.example .env
nano .env
```

Valores mínimos:

```env
DJANGO_SECRET_KEY=clave-larga-y-unica
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=sign.datain.pro
DJANGO_CSRF_TRUSTED_ORIGINS=https://sign.datain.pro
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_SECURE_HSTS_PRELOAD=True
APP_DOMAIN=sign.datain.pro
APP_USE_HTTPS=True
DATABASE_URL=postgresql://signature_user:strong-password@127.0.0.1:5432/signature_service
ZAPSIGN_API_TOKEN=tu-token
ZAPSIGN_ENVIRONMENT=sandbox
ZAPSIGN_WEBHOOK_SECRET=tu-secret
ZAPSIGN_WEBHOOK_HEADER=X-ZapSign-Secret
```

## 6. Migrar y recolectar estáticos

```bash
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

## 7. Probar Gunicorn manualmente

```bash
source venv/bin/activate
gunicorn -c deploy/gunicorn.conf.py config.wsgi:application
```

Verifica:

- `http://127.0.0.1:8001/health/`

## 8. Registrar servicio systemd

```bash
sudo cp deploy/systemd/signature_service.service /etc/systemd/system/signature_service.service
sudo systemctl daemon-reload
sudo systemctl enable signature_service
sudo systemctl start signature_service
sudo systemctl status signature_service
```

Logs:

```bash
sudo journalctl -u signature_service -f
```

## 9. Configurar Nginx

```bash
sudo cp deploy/nginx/sign.datain.pro.conf /etc/nginx/sites-available/sign.datain.pro
sudo ln -s /etc/nginx/sites-available/sign.datain.pro /etc/nginx/sites-enabled/sign.datain.pro
sudo nginx -t
sudo systemctl reload nginx
```

## 10. Apuntar subdominio

En DNS crea un registro:

- tipo `A`
- host `sign`
- valor `IP_DEL_VPS`

Si usarás `app.datain.pro`, cambia:

- `server_name` en Nginx
- `APP_DOMAIN`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`

## 11. HTTPS

Instala certificado con Let's Encrypt:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d sign.datain.pro
```

## 12. Verificaciones finales

- `https://sign.datain.pro/health/`
- `https://sign.datain.pro/signatures/`
- `https://sign.datain.pro/api/signatures/`
- webhook en `https://sign.datain.pro/api/webhooks/signatures/`

## Problemas típicos

- `400 Bad Request`: revisar `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS`
- `502 Bad Gateway`: revisar `systemctl status signature_service` y `journalctl -u signature_service -f`
- estáticos no cargan: ejecutar `collectstatic` y revisar alias en Nginx
- uploads fallan: revisar permisos sobre `/var/www/signature_service/media`
