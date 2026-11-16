"""
Celery task: process_pr_review

Flow:
  1. Load review record from DB
  2. Find the repo + user (to get GitHub access token)
  3. Fetch PR diff from GitHub
  4. Parse diff → FileDiff objects
  5. Run ReviewOrchestrator (rules + optional ML)
  6. Save FileComment objects to DB
  7. Post review comments back to GitHub PR
  8. Mark review as completed
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models.review import PRReview
from app.db.models.repository import Repository
from app.db.models.user import User
from app.db.models.comment import ReviewComment
from app.reviewer.diff_parser import parse_diff
from app.reviewer.orchestrator import orchestrator
from app.core.github import GitHubClient


def _run_async(coro):
    """Run an async coroutine from sync Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,     # 30s between retries
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_pr_review(self, review_id: int):
    """Main Celery task: review a PR end-to-end."""
    db = SessionLocal()
    try:
        # ── 1. Load review ────────────────────────────────────────────────────
        review = db.query(PRReview).filter(PRReview.id == review_id).first()
        if not review:
            print(f"[TASK] Review {review_id} not found — skipping.")
            return

        review.status = "running"
        db.commit()

        # ── 2. Load repo + user ───────────────────────────────────────────────
        repo = db.query(Repository).filter(Repository.id == review.repo_id).first()
        user = db.query(User).filter(User.id == repo.user_id).first()

        owner, repo_name = repo.full_name.split("/", 1)
        gh = GitHubClient(user.access_token)

        # ── 3. Fetch PR diff + info ────────────────────────────────────────────
        diff_text = _run_async(gh.get_pr_diff(owner, repo_name, review.pr_number))
        pr_info = _run_async(gh.get_pr_info(owner, repo_name, review.pr_number))

        # Update PR metadata if missing
        if not review.pr_title:
            review.pr_title = pr_info.get("title")
            review.pr_author = pr_info["user"]["login"]
            review.commit_sha = pr_info["head"]["sha"]

        # ── 4. Parse diff ──────────────────────────────────────────────────────
        files = parse_diff(diff_text)
        print(f"[TASK] PR #{review.pr_number} — {len(files)} changed files")

        # ── 5. Run reviewer ────────────────────────────────────────────────────
        comments = orchestrator.run(files)
        print(f"[TASK] Found {len(comments)} issue(s)")

        # ── 6. Save comments to DB ─────────────────────────────────────────────
        db_comments = []
        for c in comments:
            db_comment = ReviewComment(
                review_id=review.id,
                file_path=c.file_path,
                line_number=c.line_number,
                severity=c.severity,
                category=c.category,
                message=c.message,
                suggestion=c.suggestion,
            )
            db.add(db_comment)
            db_comments.append(db_comment)

        review.total_issues = len(comments)

        # Build human-readable summary
        errors = sum(1 for c in comments if c.severity == "error")
        warnings = sum(1 for c in comments if c.severity == "warning")
        infos = sum(1 for c in comments if c.severity == "info")

        review.summary = (
            f"CodeSheriff found **{len(comments)} issue(s)** in this PR: "
            f"{errors} error(s), {warnings} warning(s), {infos} suggestion(s).\n\n"
            f"Reviewed {len(files)} file(s)."
        ) if comments else (
            "✅ CodeSheriff found no issues in this PR. Great work!"
        )

        db.commit()

        # ── 7. Post review to GitHub ───────────────────────────────────────────
        gh_comments = [
            {
                "path": c.file_path,
                "line": c.line_number,
                "body": _format_github_comment(c),
            }
            for c in comments
            if c.line_number
        ]

        _run_async(gh.post_review(
            owner=owner,
            repo=repo_name,
            pr_number=review.pr_number,
            commit_sha=review.commit_sha or pr_info["head"]["sha"],
            body=review.summary,
            comments=gh_comments,
        ))

        # ── 8. Mark completed ──────────────────────────────────────────────────
        review.status = "completed"
        review.completed_at = datetime.now(timezone.utc)
        db.commit()

        print(f"[TASK] Review {review_id} completed ✅")

    except Exception as exc:
        # Mark as failed in DB on final retry exhaustion
        try:
            review = db.query(PRReview).filter(PRReview.id == review_id).first()
            if review and self.request.retries >= self.max_retries:
                review.status = "failed"
                db.commit()
        except Exception:
            pass
        raise exc
    finally:
        db.close()


def _format_github_comment(c) -> str:
    """Format a FileComment as a GitHub markdown review comment."""
    icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(c.severity, "⚪")
    category_label = c.category.upper()
    body = f"{icon} **[{category_label}]** {c.message}"
    if c.suggestion:
        body += f"\n\n> 💡 **Suggestion:** {c.suggestion}"
    body += "\n\n---\n*Posted by [CodeSheriff](https://github.com) 🤠*"
    return body
