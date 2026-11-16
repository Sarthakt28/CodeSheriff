from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.repository import Repository
from app.db.models.review import PRReview
from app.db.models.comment import ReviewComment
from app.core.security import get_current_user
from app.core.github import GitHubClient

router = APIRouter(prefix="/api", tags=["Reviews"])


# ── Repositories ──────────────────────────────────────────────────────────────

@router.get("/repos")
async def list_repos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all repos the user has connected to CodeSheriff."""
    repos = db.query(Repository).filter(Repository.user_id == current_user.id).all()
    return [
        {
            "id": r.id,
            "full_name": r.full_name,
            "github_repo_id": r.github_repo_id,
            "is_active": r.is_active,
            "created_at": r.created_at,
        }
        for r in repos
    ]


@router.post("/repos/sync")
async def sync_github_repos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetch repos from GitHub and upsert them into our DB.
    Call this after login to populate the user's repo list.
    """
    gh = GitHubClient(current_user.access_token)
    try:
        gh_repos = await gh.list_repos()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub API error: {e}")

    synced = []
    for gh_repo in gh_repos:
        repo = db.query(Repository).filter(
            Repository.github_repo_id == gh_repo["id"]
        ).first()
        if not repo:
            repo = Repository(
                user_id=current_user.id,
                github_repo_id=gh_repo["id"],
                full_name=gh_repo["full_name"],
                is_active=False,  # disabled by default until user opts in
            )
            db.add(repo)
        synced.append(gh_repo["full_name"])

    db.commit()
    return {"synced": len(synced), "repos": synced}


@router.patch("/repos/{repo_id}/toggle")
def toggle_repo(
    repo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enable or disable CodeSheriff reviews for a repo."""
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.user_id == current_user.id,
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo.is_active = not repo.is_active
    db.commit()
    db.refresh(repo)
    return {"id": repo.id, "full_name": repo.full_name, "is_active": repo.is_active}


# ── Reviews ───────────────────────────────────────────────────────────────────

@router.get("/reviews")
def list_reviews(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all PR reviews for the authenticated user (paginated)."""
    # Join reviews → repos → filter by user
    reviews = (
        db.query(PRReview)
        .join(Repository, PRReview.repo_id == Repository.id)
        .filter(Repository.user_id == current_user.id)
        .order_by(PRReview.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "repo_id": r.repo_id,
            "pr_number": r.pr_number,
            "pr_title": r.pr_title,
            "pr_author": r.pr_author,
            "status": r.status,
            "total_issues": r.total_issues,
            "created_at": r.created_at,
            "completed_at": r.completed_at,
        }
        for r in reviews
    ]


@router.get("/reviews/{review_id}")
def get_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single PR review with all its inline comments."""
    review = (
        db.query(PRReview)
        .join(Repository, PRReview.repo_id == Repository.id)
        .filter(PRReview.id == review_id, Repository.user_id == current_user.id)
        .first()
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    comments = db.query(ReviewComment).filter(
        ReviewComment.review_id == review_id
    ).order_by(ReviewComment.file_path, ReviewComment.line_number).all()

    return {
        "id": review.id,
        "repo_id": review.repo_id,
        "pr_number": review.pr_number,
        "pr_title": review.pr_title,
        "pr_author": review.pr_author,
        "commit_sha": review.commit_sha,
        "status": review.status,
        "summary": review.summary,
        "total_issues": review.total_issues,
        "created_at": review.created_at,
        "completed_at": review.completed_at,
        "comments": [
            {
                "id": c.id,
                "file_path": c.file_path,
                "line_number": c.line_number,
                "severity": c.severity,
                "category": c.category,
                "message": c.message,
                "suggestion": c.suggestion,
            }
            for c in comments
        ],
    }
