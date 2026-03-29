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

## Notes
- Contract source: `docs/phase-0/03-api-contract-openapi.yaml`
- DB schema source: `docs/phase-0/schema.sql`
