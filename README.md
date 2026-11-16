<div align="center">

# 🤠 CodeSheriff

### Automated, Multi-Engine AI Code Review Platform for GitHub Pull Requests

[![CI Pipeline](https://github.com/Sarthakt28/CodeSheriff/actions/workflows/ci.yml/badge.svg)](https://github.com/Sarthakt28/CodeSheriff/actions)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.0-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![Celery](https://img.shields.io/badge/Celery-5.7+-37814A.svg?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D.svg?logo=redis&logoColor=white)](https://redis.io/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-v3-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**CodeSheriff** is an autonomous, developer-first code review platform. Powered by a hybrid engine combining deterministic lexical analysis with semantic neural embeddings, CodeSheriff automatically inspects pull requests, detects syntax bugs, security vulnerabilities, and anti-patterns, and posts targeted inline review comments directly to GitHub code diffs within seconds.

[Explore Features](#-key-features) • [Architecture](#-system-architecture) • [Quickstart](#-quickstart-guide) • [ML Engine](#-machine-learning-engine) • [API & Webhooks](#-webhooks--github-app-integration) • [Production Deployment](#-production-deployment)

---

</div>

## 🌟 Key Features

### 🔍 1. Dual-Core Review Engine
- **Deterministic Lexical Analysis (Pygments)**: High-speed AST & lexer scanning for:
  - 🚨 **Secret & Credential Detection**: Catches committed API tokens, AWS keys, passwords, and private SSH/RSA keys before they hit production.
  - ⚠️ **Syntax & Parsing Errors**: Language-aware token error detection across 20+ programming languages.
  - 📏 **Style & Maintainability Guardrails**: Flags long lines (>120 chars), abandoned `TODO`/`FIXME` items, leftover debug statements (`print()`, `console.log`), and missing function docstrings.
  - 🧩 **Complexity Checks**: Identifies bloated functions (>50 lines) and dead commented-out code blocks.
- **Semantic Neural Analysis (Hugging Face)**:
  - Vector cosine similarity engine using `all-MiniLM-L6-v2` SentenceTransformers.
  - Detects semantic vulnerabilities: SQL injection patterns, race conditions, unsanitized user inputs, and broad exception swallowing.

### ⚡ 2. High-Throughput Asynchronous Pipeline
- **Instant Webhook Ingestion**: Webhook endpoints respond within `<10ms` to GitHub, acknowledging receipt and avoiding timeouts.
- **Distributed Celery Queue**: Review workloads are offloaded to Redis-backed Celery workers, complete with exponential backoff and automatic retry policies.
- **Unified Diff Parsing**: Accurately parses Git patch hunks, calculating precise real-world line coordinates to avoid ghost comments.

### 🎨 3. Modern Real-Time Dashboard
- **React 19 & Tailwind CSS**: Modern dark-mode interface with live review metric tracking.
- **1-Click OAuth Integration**: Sign in with GitHub, discover your private & public repositories, and toggle continuous code reviews with a single switch.
- **Drilldown Review Inspector**: Visual severity chips (`Error`, `Warning`, `Info`), file-by-file grouping, and automated fix suggestions.

---

## 🏛️ System Architecture

```
                       ┌────────────────────────┐
                       │  GitHub Pull Request   │
                       └───────────┬────────────┘
                                   │  1. Webhook (pull_request.opened / sync)
                                   ▼
                       ┌────────────────────────┐
                       │    Smee Proxy / TLS    │
                       └───────────┬────────────┘
                                   │  2. HMAC-SHA256 Payload
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ CodeSheriff Backend (FastAPI :8000)                                   │
│  ├── 3. Signature Verification (_verify_github_signature)             │
│  ├── 4. Persistence (User, Repository, PRReview State)               │
│  └── 5. Task Dispatch (process_pr_review.delay)                       │
└──────────────────────────────────┬────────────────────────────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │  Redis Broker (:6379)  │
                       └───────────┬────────────┘
                                   │  6. Pop Task Job
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Distributed Celery Worker                                             │
│  ├── 7. GitHub Diff Extraction (httpx AsyncClient)                    │
│  ├── 8. Unified Diff Parser (line number coordinate mapping)          │
│  ├── 9. Review Orchestrator:                                          │
│  │     ├── RulesReviewer (Pygments Lexical Scanner)                   │
│  │     └── MLReviewer (SentenceTransformer Embeddings)                │
│  ├── 10. Severity Ranking & Comment Deduplication                    │
│  └── 11. GitHub PR Review Posting (POST /pulls/{id}/reviews)          │
└──────────────────────────────────┬────────────────────────────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │  PostgreSQL / SQLite   │
                       └───────────┬────────────┘
                                   │  12. Sync State & Metrics
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ CodeSheriff Frontend Dashboard (React 19 + Vite :5173)                │
│  └── Real-time review breakdowns, repository toggles, security stats  │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart Guide

### Prerequisites
- **Python**: `>= 3.11`
- **Node.js**: `>= 18.0.0`
- **Docker**: (Optional, for Redis/PostgreSQL containerization)

---

### Step 1: Clone Repository
```bash
git clone https://github.com/Sarthakt28/CodeSheriff.git
cd CodeSheriff
```

---

### Step 2: Configure Environment Variables

1. **Backend Environment**:
```bash
cp backend/.env.example backend/.env
```
Edit `backend/.env` with your parameters:
```env
# GitHub OAuth & Webhooks
GITHUB_CLIENT_ID=your_oauth_client_id
GITHUB_CLIENT_SECRET=your_oauth_client_secret
GITHUB_WEBHOOK_SECRET=your_custom_webhook_secret

# Security & DB
JWT_SECRET=your_super_secret_jwt_key
DATABASE_URL=sqlite:///D:/CodeSheriff/codesheriff_local.db
REDIS_URL=redis://localhost:6379/0

# ML Reviewer Toggle
USE_ML_REVIEWER=false
```

2. **Frontend Environment**:
```bash
cp frontend/.env.example frontend/.env
```
Edit `frontend/.env`:
```env
VITE_GITHUB_CLIENT_ID=your_oauth_client_id
```

---

### Step 3: Start Supporting Infrastructure (Redis)

If using Docker:
```bash
docker run -d -p 6379:6379 --name sheriff-redis redis:7-alpine
```

---

### Step 4: Run Services

Open three dedicated terminal windows:

#### Terminal 1 — FastAPI Backend:
```bash
cd backend
pip install -r requirements.txt
python main.py
# API running at http://localhost:8000 (Swagger docs: http://localhost:8000/docs)
```

#### Terminal 2 — Celery Background Worker:
```bash
cd backend
# On Windows:
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo

# On Linux/macOS:
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
```

#### Terminal 3 — React Dashboard:
```bash
cd frontend
npm install
npm run dev
# Dashboard running at http://localhost:5173
```

---

## 🔗 Webhooks & GitHub Integration

CodeSheriff is designed to review pull requests without requiring manual intervention.

### Local Development Webhook Relay (smee.io)
When developing locally without a public IP, use the included tunnel helper:

```bash
# Install smee client globally
npm install -g smee-client

# Start the webhook proxy
python setup_webhook_tunnel.py
```

### GitHub Webhook Configuration:
1. Navigate to your target GitHub repository: **Settings > Webhooks > Add webhook**.
2. **Payload URL**: Enter your Smee URL (or your production domain endpoint: `https://your-domain.com/webhooks/github`).
3. **Content type**: `application/json`.
4. **Secret**: Enter the exact secret specified in `GITHUB_WEBHOOK_SECRET`.
5. **Events**: Select **"Let me select individual events"** and enable **Pull requests**.
6. Click **Add webhook**.

---

## 🧠 Machine Learning Engine

CodeSheriff features an extensible AI review architecture located in `ml/`.

### 1. Zero-Shot Semantic Review (`ml_reviewer.py`)
Uses `sentence-transformers/all-MiniLM-L6-v2` to compute vector embeddings of diff chunks and measures cosine similarity against curated security and style anchor patterns.

Enable in `backend/.env`:
```env
USE_ML_REVIEWER=true
ML_MODEL_NAME=all-MiniLM-L6-v2
```

### 2. Standalone Code Inference CLI (`ml/infer.py`)
Test arbitrary files or snippets through the review pipeline without needing active GitHub events:

```bash
# Analyze a Python script via zero-shot embeddings
python ml/infer.py --file backend/app/api/auth.py

# Inline code analysis
python ml/infer.py --code "password = 'admin' \n eval(user_input)"
```

### 3. Model Fine-Tuning (`ml/train.py`)
Fine-tune sequence classification models (e.g., `Salesforce/codet5-base`) on custom team-specific review datasets:

```bash
python ml/train.py \
  --data ml/data/labeled_data.jsonl \
  --output ml/models/severity_classifier \
  --epochs 5 \
  --batch-size 8
```

---

## 🧪 Testing & Verification

CodeSheriff includes a comprehensive test suite covering diff hunk extraction, lexical rules, security filters, and async task execution:

```bash
cd backend
pytest tests/ -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.14.4, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\CodeSheriff\backend
configfile: pytest.ini

backend/tests/test_diff_parser.py ...........                            [ 34%]
backend/tests/test_rules_reviewer.py .....................               [100%]

============================= 32 passed in 0.14s ==============================
```

---

## 🐳 Production Deployment

CodeSheriff includes a production-ready container stack orchestrating PostgreSQL, Redis, multi-worker FastAPI, Celery, and Nginx reverse proxy.

```bash
# Copy and fill production secrets
cp backend/.env .env.prod

# Launch stack in background
docker compose -f docker-compose.prod.yml up -d --build
```

### Container Stack Architecture:
| Service | Image | Internal Port | Description |
|---|---|---|---|
| `db` | `postgres:16-alpine` | `5432` | Primary database with persistent volume |
| `redis` | `redis:7-alpine` | `6379` | LRU task queue broker with persistent disk state |
| `api` | `codesheriff-api` | `8000` | 4-worker Uvicorn ASGI server |
| `worker` | `codesheriff-api` | — | Concurrency-4 Celery processing daemon |
| `frontend` | `codesheriff-frontend` | `80, 443` | Nginx Alpine hosting production React SPA |

---

## 📂 Project Directory Structure

```
CodeSheriff/
├── .github/
│   └── workflows/
│       └── ci.yml                     # Automated GitHub Actions test pipeline
├── backend/
│   ├── app/
│   │   ├── api/                       # REST endpoints (auth, reviews, webhooks)
│   │   │   ├── auth.py                # GitHub OAuth token exchange & user sync
│   │   │   ├── reviews.py             # Repositories & reviews queries
│   │   │   └── webhook.py             # HMAC validation & event routing
│   │   ├── core/                      # Application config & security primitives
│   │   │   ├── config.py              # Pydantic BaseSettings management
│   │   │   ├── github.py              # Asynchronous GitHub REST API client
│   │   │   └── security.py            # JWT token signing & verification
│   │   ├── db/                        # Database schema & connection pooling
│   │   │   ├── models/                # User, Repository, PRReview, ReviewComment
│   │   │   └── session.py             # Engine initialization & fallback logic
│   │   ├── reviewer/                  # Core code analysis engines
│   │   │   ├── base.py                # BaseReviewer abstract class
│   │   │   ├── diff_parser.py         # Unified diff chunk parser & line mapper
│   │   │   ├── ml_reviewer.py         # Neural vector similarity engine
│   │   │   ├── models.py              # FileDiff & FileComment dataclasses
│   │   │   ├── orchestrator.py        # Multi-engine review aggregator
│   │   │   └── rules_reviewer.py      # Pygments deterministic rules engine
│   │   └── tasks/                     # Celery background tasks
│   │       ├── celery_app.py          # Celery worker initialization
│   │       └── review_task.py         # PR processing pipeline
│   ├── tests/                         # Pytest test suite (32 unit tests)
│   ├── Dockerfile                     # Python 3.11 production container
│   ├── main.py                        # Uvicorn entrypoint
│   └── requirements.txt               # Backend dependencies
├── frontend/
│   ├── src/
│   │   ├── components/                # Reusable UI components (Navbar, CommentCard)
│   │   ├── lib/api.ts                 # Axios client with interceptors
│   │   ├── pages/                     # Dashboard, Repositories, Reviews, ReviewDetail
│   │   └── types/index.ts             # TypeScript domain definitions
│   ├── Dockerfile                     # Multi-stage Node builder & Nginx runner
│   ├── nginx.conf                     # Nginx SPA proxy & routing
│   └── package.json                   # React 19 dependencies
├── ml/
│   ├── data/labeled_data.jsonl        # Dataset for training severity classifier
│   ├── infer.py                       # CLI tool for offline code inference
│   └── train.py                       # CodeT5 model fine-tuning script
├── docker-compose.yml                 # Local development stack
├── docker-compose.prod.yml            # Production deployment stack
├── setup_webhook_tunnel.py            # Automated Smee.io tunnel runner
└── README.md
```

---

## 🔒 Security & Standards

- **HMAC-SHA256 Webhook Validation**: Every incoming GitHub webhook request is verified using timing-safe comparison (`hmac.compare_digest`) before execution.
- **JWT Cryptographic Sessions**: Stateless authentication with signature verification for all protected dashboard REST APIs.
- **Zero Credentials in Version Control**: Strict `.gitignore` configurations safeguarding local databases (`.db`), environment files (`.env`), and machine learning model checkpoints.

---

## 📄 License

CodeSheriff is released under the [MIT License](LICENSE).
Built with ❤️ by [Sarthak Tiwari](https://github.com/Sarthakt28).
