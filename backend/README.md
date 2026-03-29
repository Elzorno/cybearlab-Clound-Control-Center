# Backend (Phase 1 Starter)

## Run locally
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open:
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

Default bootstrap login:
- Username: `admin`
- Password: `change-me-now`
- Override with env vars: `BOOTSTRAP_ADMIN_USERNAME`, `BOOTSTRAP_ADMIN_PASSWORD`
- Admin execution mode defaults to `mock`; set `EXECUTION_MODE=live` to run real scripts via `sudo -n`.

Quick login test:
```bash
curl -sS -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"change-me-now"}'
```

Roster upload test (requires bearer token):
```bash
curl -sS -X POST http://127.0.0.1:8000/admin/uploads/roster \
  -H "Authorization: Bearer <TOKEN>" \
  -F "roster=@./sample.xlsx"
```

Run a grade (currently synchronous in request path):
```bash
curl -sS -X POST http://127.0.0.1:8000/grader/runs \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'
```

## Notes
- Contract source: `docs/phase-0/03-api-contract-openapi.yaml`
- DB schema source: `docs/phase-0/schema.sql`
- Current persistence default: local SQLite file `backend/iscs1800.db` (set `DATABASE_URL` to use PostgreSQL).

## Deployment on `admin.cybearlab.cloud`
- Run the backend as a persistent systemd service bound to `127.0.0.1:8000`.
- Proxy `/api/` from Nginx to `http://127.0.0.1:8000/` so the browser can use a same-origin API base.
- Disable site-level Basic Auth on `/api/` so Bearer tokens can reach FastAPI without conflicting in the `Authorization` header.
- Keep `public/api-proxy.php` as a fallback for environments where the reverse proxy is unavailable.
