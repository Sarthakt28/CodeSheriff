import hashlib
import hmac
from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.repository import Repository
from app.db.models.review import PRReview
from app.core.config import settings

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _verify_github_signature(payload: bytes, signature_header: str) -> bool:
    """Validate the X-Hub-Signature-256 HMAC from GitHub."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    received = signature_header[len("sha256="):]
    return hmac.compare_digest(expected, received)


@router.post("/github")
async def github_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
):
    """
    Receive GitHub webhook events.
    Currently handles: pull_request (opened, synchronize, reopened)
    """
    raw_body = await request.body()

    # 1. Validate HMAC signature
    if settings.GITHUB_WEBHOOK_SECRET:
        if not _verify_github_signature(raw_body, x_hub_signature_256 or ""):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    # 2. Only process pull_request events
    if x_github_event != "pull_request":
        return {"status": "ignored", "event": x_github_event}

    payload = await request.json()
    action = payload.get("action")

    # 3. Only trigger on opened / reopened / synchronize (new commits pushed)
    if action not in ("opened", "reopened", "synchronize"):
        return {"status": "ignored", "action": action}

    pr = payload["pull_request"]
    repo_data = payload["repository"]

    repo_github_id = repo_data["id"]
    pr_number = pr["number"]
    pr_title = pr["title"]
    pr_author = pr["user"]["login"]
    commit_sha = pr["head"]["sha"]

    # 4. Find the repo in our DB (must be active)
    repo = db.query(Repository).filter(
        Repository.github_repo_id == repo_github_id,
        Repository.is_active == True,
    ).first()

    if not repo:
        return {"status": "skipped", "reason": "repo not registered or inactive"}

    # 5. Create a pending review record
    review = PRReview(
        repo_id=repo.id,
        pr_number=pr_number,
        pr_title=pr_title,
        pr_author=pr_author,
        commit_sha=commit_sha,
        status="pending",
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    # 6. Enqueue Celery task (imported here to avoid circular imports)
    from app.tasks.review_task import process_pr_review
    process_pr_review.delay(review.id)

    return {"status": "queued", "review_id": review.id, "pr": pr_number}
