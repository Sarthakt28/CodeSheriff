from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.repository import Repository
from app.core.github import GitHubClient, exchange_code_for_token
from app.core.security import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/github")
async def github_oauth_callback(code: str, db: Session = Depends(get_db)):
    """
    GitHub OAuth callback.
    Exchange the code for a GitHub access token, upsert the user, return JWT.
    """
    # 1. Exchange code → GitHub access token
    try:
        github_token = await exchange_code_for_token(code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub OAuth failed: {str(e)}",
        )

    # 2. Fetch GitHub user info
    gh = GitHubClient(github_token)
    try:
        gh_user = await gh.get_user()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API error: {str(e)}",
        )

    # 3. Upsert user in our DB
    user = db.query(User).filter(User.github_id == gh_user["id"]).first()
    if user:
        user.github_username = gh_user["login"]
        user.github_email = gh_user.get("email")
        user.avatar_url = gh_user.get("avatar_url")
        user.access_token = github_token
    else:
        user = User(
            github_id=gh_user["id"],
            github_username=gh_user["login"],
            github_email=gh_user.get("email"),
            avatar_url=gh_user.get("avatar_url"),
            access_token=github_token,
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    # 4. Create JWT and return it
    jwt_token = create_access_token(user.id)
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.github_username,
            "avatar_url": user.avatar_url,
        },
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return {
        "id": current_user.id,
        "github_id": current_user.github_id,
        "username": current_user.github_username,
        "email": current_user.github_email,
        "avatar_url": current_user.avatar_url,
        "created_at": current_user.created_at,
    }
