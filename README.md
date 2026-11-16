# CodeSheriff 🤠

> **Automated AI code review for every pull request.**  
> GitHub OAuth login → install on repos → every PR gets reviewed automatically.

---

## Features

| | |
|---|---|
| 🔍 **8 Rules-based checks** | Secrets, syntax errors, long lines, TODOs, print statements, missing docstrings, large functions, commented-out code |
| 🧠 **ML semantic analysis** | SentenceTransformer embeddings detect SQL injection, race conditions, broad exceptions, and more |
| 🔗 **GitHub native** | Reviews posted directly on PRs as inline comments |
| 📊 **Dashboard** | React frontend shows review history, severity breakdowns, per-file issues |
| ⚡ **Async pipeline** | FastAPI + Celery + Redis — webhook returns instantly, review runs in background |

---

## Architecture

```
GitHub Webhook
      │
      ▼
  FastAPI (port 8000)
      │  validates HMAC-SHA256
      │  saves PRReview to DB
      │  enqueues task
      ▼
  Redis (broker)
      │
      ▼
  Celery Worker
      │  fetches PR diff from GitHub API
      │  RulesReviewer + MLReviewer
      │  saves comments to DB
      │  posts review to GitHub
      ▼
  PostgreSQL / SQLite
      │
      ▼
  React Frontend (port 5173 / 80)
```

---

## Quick Start (Local Dev)

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### 1. Clone & configure

```bash
git clone https://github.com/YOUR_USERNAME/CodeSheriff.git
cd CodeSheriff
```

### 2. Create a GitHub OAuth App

1. Go to [github.com/settings/applications/new](https://github.com/settings/applications/new)
2. Set:
   - **Homepage URL:** `http://localhost:5173`
   - **Callback URL:** `http://localhost:5173/auth/callback`
3. Copy **Client ID** and **Client Secret**

### 3. Configure backend

```bash
cd backend
cp .env.example .env     # or edit .env directly
```

Edit `backend/.env`:
```env
GITHUB_CLIENT_ID=YOUR_CLIENT_ID
GITHUB_CLIENT_SECRET=YOUR_CLIENT_SECRET
GITHUB_WEBHOOK_SECRET=any_random_string_32chars
JWT_SECRET_KEY=another_random_secret_key
DATABASE_URL=sqlite:///./codesheriff.db    # SQLite for local dev
REDIS_URL=redis://localhost:6379/0
USE_ML_REVIEWER=false                      # set true to enable ML (slow first load)
```

### 4. Install & run backend

```bash
cd backend
pip install -r requirements.txt
python main.py
# → http://localhost:8000
```

### 5. Configure & run frontend

```bash
cd frontend
cp .env.example .env
# edit .env: VITE_GITHUB_CLIENT_ID=YOUR_CLIENT_ID
npm install
npm run dev
# → http://localhost:5173
```

### 6. Open the app

Navigate to `http://localhost:5173` → click **Sign in with GitHub** → authorize → dashboard.

---

## Setting Up Webhooks

For CodeSheriff to review PRs automatically, GitHub needs to send webhooks to your server.

### Local dev (using smee.io proxy)

```bash
npm install -g smee-client
smee --url https://smee.io/YOUR_CHANNEL --target http://localhost:8000/webhooks/github
```

Then set your GitHub App's webhook URL to `https://smee.io/YOUR_CHANNEL`.

### Production

Set webhook URL to `https://YOUR_DOMAIN/webhooks/github`.

### Register the webhook

In your repo or org settings → **Webhooks** → Add webhook:
- **Payload URL:** `http://localhost:8000/webhooks/github` (or smee URL)
- **Content type:** `application/json`
- **Secret:** same value as `GITHUB_WEBHOOK_SECRET` in `.env`
- **Events:** select "Pull requests"

---

## Production Deployment (Docker)

### 1. Create `.env.prod`

```bash
cp backend/.env .env.prod
# Edit with real production values:
#   POSTGRES_PASSWORD=strong_password_here
#   GITHUB_WEBHOOK_SECRET=strong_random_secret
#   JWT_SECRET_KEY=strong_random_key
#   VITE_GITHUB_CLIENT_ID=your_prod_client_id
```

### 2. Build & deploy

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 3. Services

| Service | Port | URL |
|---------|------|-----|
| Frontend (nginx) | 80 | `http://your-domain.com` |
| API (FastAPI) | 8000 | `http://your-domain.com:8000` |
| Flower (monitoring) | 5555 | `http://your-domain.com:5555` |

Enable Flower: `docker compose -f docker-compose.prod.yml --profile monitoring up -d`

---

## ML Reviewer (Phase 2)

The ML reviewer uses `all-MiniLM-L6-v2` (SentenceTransformer) for zero-shot semantic analysis.

### Enable it

```env
USE_ML_REVIEWER=true
```

The model (~90 MB) downloads from HuggingFace on first use.

### Fine-tune on your own data

```bash
# 1. Create labeled_data.jsonl
# Format: {"code": "...", "label": "error|warning|info"}

# 2. Train
python ml/train.py --data ml/data/labeled_data.jsonl --output ml/models/my_model --epochs 5

# 3. Run inference
python ml/infer.py --file path/to/file.py
python ml/infer.py --code "password='bad'" --mode embedding
```

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

| Test file | What it covers |
|-----------|----------------|
| `test_diff_parser.py` | Unified diff parsing, line numbers, multi-hunk |
| `test_rules_reviewer.py` | All 8 rules: secrets, TODO, long lines, etc. |
| `test_webhook.py` | HMAC validation, event filtering |
| `test_review_task.py` | Full pipeline with mocked GitHub API |

---

## Project Structure

```
CodeSheriff/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes (auth, webhooks, reviews)
│   │   ├── core/          # Config, security (JWT), GitHub client
│   │   ├── db/            # SQLAlchemy models, session
│   │   ├── reviewer/      # RulesReviewer, MLReviewer, orchestrator
│   │   └── tasks/         # Celery app + review pipeline task
│   ├── tests/             # pytest unit tests
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/    # Navbar, CommentCard
│   │   ├── pages/         # Login, Dashboard, Repos, Reviews, ReviewDetail
│   │   ├── lib/           # axios API client
│   │   └── types/         # TypeScript interfaces
│   ├── Dockerfile
│   └── nginx.conf
├── ml/
│   ├── train.py           # Fine-tune CodeT5 severity classifier
│   └── infer.py           # Standalone inference CLI
├── docker-compose.yml     # Local dev stack
├── docker-compose.prod.yml # Production stack
└── .github/workflows/ci.yml
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_CLIENT_ID` | ✅ | OAuth App Client ID |
| `GITHUB_CLIENT_SECRET` | ✅ | OAuth App Client Secret |
| `GITHUB_WEBHOOK_SECRET` | ✅ | Webhook HMAC secret |
| `JWT_SECRET_KEY` | ✅ | JWT signing key |
| `DATABASE_URL` | ✅ | PostgreSQL URL (SQLite fallback) |
| `REDIS_URL` | ✅ | Redis broker URL |
| `USE_ML_REVIEWER` | ❌ | `true` to enable ML (default: `false`) |
| `ML_MODEL_NAME` | ❌ | HuggingFace model name (default: `all-MiniLM-L6-v2`) |

---

## License

MIT © 2026 CodeSheriff
