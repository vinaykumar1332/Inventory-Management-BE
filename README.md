# SealTrack Inventory: Backend

Django API and admin for SealTrack Inventory. This folder is the backend only. The Vite frontend in the parent folder is not changed by it.

Stack: Django 6.1, Django REST Framework, django-cors-headers, django-filter, PostgreSQL 16 (Docker), python-dotenv.

Current scope: local setup, PostgreSQL connection, a custom user model, signup / login / logout / me API endpoints, and Django admin. Bills, OCR, inventory, and sites are not built yet.

## Expected URLs

| What | URL |
|---|---|
| API health check | http://127.0.0.1:8000/api/health/ |
| Sign up (backend) | `POST /api/auth/signup/` |
| Log in (backend) | `POST /api/auth/login/` |
| Current user | `GET /api/auth/me/` |
| Log out | `POST /api/auth/logout/` |
| Django admin | http://127.0.0.1:8000/admin/ |
| Frontend (Vite) | http://localhost:5173 |
| Frontend login | http://localhost:5173/login |
| Frontend signup | http://localhost:5173/signup |

## Prerequisites

- **Python 3.14** from python.org. Tick "Add python.exe to PATH" in the installer. The `py` launcher is used below.
- **Docker Desktop** for Windows. Install it, start it, and wait until it says "Engine running".
- Windows PowerShell. Run every command from the `backend` folder.

Note: Windows has a fake `python` command that opens the Microsoft Store. That is why these steps use `py -3` and `.\.venv\Scripts\python.exe` rather than `python`.

## Setup (Windows PowerShell)

### 1. Create the virtual environment

```powershell
cd C:\Inventory-Mangament\Inventory-Management\backend
py -3 -m venv .venv
```

### 2. Install the requirements

Calling the venv's Python directly means you do not need to activate it, so the PowerShell script policy does not get in the way.

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Optional: if you want to activate the venv anyway, run this once first, then `.\.venv\Scripts\Activate.ps1`:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 3. Create your local `.env` file

The real `.env` is never committed. Copy the template and edit it:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set `DJANGO_SECRET_KEY` to a long random string and `POSTGRES_PASSWORD` to a local password. Use the same password wherever it appears: Docker reads it to create the database, and Django reads it to connect.

To generate a secret key:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 4. Start PostgreSQL with Docker Compose

```powershell
docker compose up -d db
docker compose ps
```

Wait until the `db` service shows `healthy`. Data is kept in the Docker volume `sealtrack_pgdata`. To delete the database and start fresh, run `docker compose down -v`.

### 5. Run migrations

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

### 6. Create an admin user

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

You will be asked for an email, a full name, and a password. The account gets the `SUPER_ADMIN` role.

### 7. Run the development server

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

### 8. Test it

In a second PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health/
```

Expected output:

```text
status service
------ -------
ok     sealtrack-api
```

Open http://127.0.0.1:8000/admin/ and sign in with the superuser email and password.

## Verifying the integrated login

Once both servers are running:

1. **Admin panel** — open http://127.0.0.1:8000/admin/ and sign in with the superuser credentials you created in step 6. You should see the Users table and be able to create or disable accounts from there.

2. **Frontend signup** — open http://localhost:5173/signup. Fill in any name, email, and a strong password (8+ characters, mixed). After submitting you should be signed in as a Site Manager and land on the dashboard.

3. **Frontend login** — open http://localhost:5173/login. Enter the email and password you just signed up with. The quick-access demo buttons still bypass the password (they use mock accounts from the seed data).

4. **Quick API test** (PowerShell):

```powershell
# Health
Invoke-RestMethod http://127.0.0.1:8000/api/health/

# Sign up a new user
$body = '{"full_name":"Test User","email":"test@example.com","password":"Sealtrack-local-2026"}'
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/auth/signup/ `
  -Method POST -ContentType "application/json" -Body $body

# (login is blocked without a CSRF token in a plain HTTP client — use the browser for it)
```

## Day-to-day

```powershell
cd C:\Inventory-Mangament\Inventory-Management\backend
docker compose up -d db
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

After changing a model:

```powershell
.\.venv\Scripts\python.exe manage.py makemigrations
.\.venv\Scripts\python.exe manage.py migrate
```

Other useful commands:

```powershell
.\.venv\Scripts\python.exe manage.py check
docker compose logs db
docker compose down        # stop the database, keep its data
```

## Configuration notes

- Settings live in `config/settings.py`. Values come from `backend/.env`, and real environment variables override the file.
- The database is PostgreSQL only. There is no SQLite fallback.
- CORS allows exactly one browser origin: `http://localhost:5173`. Do not widen it.
- Every API endpoint requires a signed-in user unless it opts out. `/api/health/` is the only public endpoint.
- The database port is bound to `127.0.0.1` in `docker-compose.yml`, so it is not reachable from other machines.
- Time zone is `Asia/Kolkata`, and timestamps are stored in UTC (`USE_TZ = True`).

## Layout

```text
backend/
  config/           Project settings, root URLs, WSGI/ASGI, health view
  accounts/         Custom user model (email login, roles), admin
  manage.py
  requirements.txt  Pinned versions
  docker-compose.yml
  .env.example      Template, copy to .env
```

API prefixes reserved for later apps: `/api/auth/`, `/api/sites/`, `/api/products/`, `/api/inventory/`.

## Troubleshooting

- **"running scripts is disabled" when activating**: you do not need to activate. Use `.\.venv\Scripts\python.exe` as shown above, or run the `Set-ExecutionPolicy` line in step 2.
- **"Python was not found" / Microsoft Store opens**: use `py -3` to create the venv and `.\.venv\Scripts\python.exe` for everything else. Do not use bare `python`.
- **"docker is not recognized"**: Docker Desktop is not installed or not on PATH. Install it, reopen PowerShell, and start Docker Desktop.
- **`RuntimeError: DJANGO_SECRET_KEY is not set`**: `.env` is missing or in the wrong folder. It must be `backend\.env`.
- **`docker compose` fails with `POSTGRES_PASSWORD`**: the value is missing from `backend\.env`.
- **`password authentication failed`**: the password in `.env` does not match the one the database was first created with. Restore that password, or run `docker compose down -v` (this deletes the database) and start again.
- **`connection timeout expired` or `connection refused` on port 5432**: the `db` container is not running or not healthy. Check `docker compose ps`.
- **Port 5432 already in use**: a local PostgreSQL install is running. Stop it, or change the host port in `docker-compose.yml` and `POSTGRES_PORT` in `.env`.
