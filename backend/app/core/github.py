import httpx
from app.core.config import settings


class GitHubClient:
    """Async GitHub API client using the user's OAuth access token."""

    BASE_URL = "https://api.github.com"

    def __init__(self, access_token: str):
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_user(self) -> dict:
        """Get authenticated GitHub user info."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/user", headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Fetch the unified diff of a pull request."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        diff_headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=diff_headers)
            resp.raise_for_status()
            return resp.text

    async def get_pr_info(self, owner: str, repo: str, pr_number: int) -> dict:
        """Fetch PR metadata (title, author, head SHA)."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def post_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_sha: str,
        body: str,
        comments: list[dict],
    ) -> dict:
        """
        Post a review with inline comments to a PR.

        Each comment dict: { path, line, body }
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        payload = {
            "commit_id": commit_sha,
            "body": body,
            "event": "COMMENT",   # COMMENT | REQUEST_CHANGES | APPROVE
            "comments": [
                {
                    "path": c["path"],
                    "line": c["line"],
                    "body": c["body"],
                }
                for c in comments
                if c.get("line")  # GitHub requires a valid line number
            ],
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self.headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def list_repos(self) -> list[dict]:
        """List all repos the authenticated user has access to."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/user/repos",
                headers=self.headers,
                params={"per_page": 100, "sort": "updated"},
            )
            resp.raise_for_status()
            return resp.json()


async def exchange_code_for_token(code: str) -> str:
    """Exchange GitHub OAuth code for an access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise ValueError(f"GitHub OAuth error: {data['error_description']}")
        return data["access_token"]
