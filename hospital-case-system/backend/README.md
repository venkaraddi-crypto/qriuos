# ArogyaSetu backend

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/uvicorn app.main:app --reload --port 8000   # docs at http://localhost:8000/docs
.venv/bin/pytest tests/ -q
```

See ../README.md for configuration and architecture.
