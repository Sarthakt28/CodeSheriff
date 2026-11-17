from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.base import Base
from app.db.session import engine
from app.core.config import settings
from app.api.webhook import router as webhook_router
from app.api.auth import router as auth_router
from app.api.reviews import router as reviews_router

# ── Create all DB tables on startup ──────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="CodeSheriff API",
    description="Automated AI code review platform — GitHub App integration",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Explicitly allow local dev and production onrender.com domains.
# Note: W3C CORS spec forbids allow_origins=["*"] when allow_credentials=True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://codesheriff-frontend.onrender.com",
    ],
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(webhook_router)
app.include_router(auth_router)
app.include_router(reviews_router)


# ── Health & Root ─────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "CodeSheriff API — visit /docs for Swagger UI"}


@app.get("/health")
def health():
    return {"status": "healthy", "service": "CodeSheriff"}
