"""Forgejo/Gitea issue client — M10 question triage pipeline.

Student questions are mirrored to a Forgejo issue whose labels track the LLM
lifecycle: LLM_BACKLOG -> LLM_WIP -> LLM_DONE -> (HUMAN_VERIFIED | REJECTED).
Labels are applied as a unique set and replaced cleanly, never duplicated.

Auth: personal access token via `FORGEJO_TOKEN`, falling back to `GITEA_TOKEN`.
The token is sent as `Authorization: token <token>` (Gitea/Forgejo convention).
"""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Polelo-managed labels and their default colours/descriptions.
POLELO_LABELS: dict[str, dict[str, str]] = {
    "LLM_BACKLOG": {"color": "d4c5f9", "description": "New question awaiting an LLM answer"},
    "LLM_WIP": {"color": "bfd4f2", "description": "Question being answered by the LLM engine"},
    "LLM_DONE": {"color": "0e8a16", "description": "LLM answer generated and stored"},
    "LLM_SIMILAR": {"color": "e4e669", "description": "A similar question already exists"},
    "HUMAN_BACKLOG": {"color": "c2e0c6", "description": "Answer awaiting teacher/parent verification"},
    "HUMAN_VERIFIED": {"color": "128a0c", "description": "Answer verified by a teacher or parent"},
    "REJECTED": {"color": "d73a4a", "description": "Answer rejected, sent back for regeneration"},
}

DEFAULT_TIMEOUT = 15.0


class ForgejoClient:
    """Async client for the Forgejo/Gitea issues REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        owner: str | None = None,
        repo: str | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.base_url = (base_url or os.getenv("FORGEJO_URL", "")).rstrip("/")
        self.token = token or os.getenv("FORGEJO_TOKEN") or os.getenv("GITEA_TOKEN", "")
        self.owner = owner or os.getenv("FORGEJO_OWNER", "")
        self.repo = repo or os.getenv("FORGEJO_REPO", "")
        self._client = client or httpx.AsyncClient(
            base_url=f"{self.base_url}/api/v1",
            timeout=DEFAULT_TIMEOUT,
            headers={"Authorization": f"token {self.token}"} if self.token else {},
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.token and self.owner and self.repo)

    # -- Internal helpers -------------------------------------------------

    def _repo_path(self, suffix: str = "") -> str:
        return f"/repos/{self.owner}/{self.repo}{suffix}"

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.is_error:
            logger.error("Forgejo API error %s: %s", resp.status_code, resp.text[:300])
            resp.raise_for_status()

    # -- Labels -----------------------------------------------------------

    async def ensure_labels(self) -> dict[str, int]:
        """Create any missing Polelo labels. Returns mapping label name -> label id."""
        existing = await self.list_labels()
        label_map: dict[str, int] = {}
        for label in existing:
            name = label.get("name", "")
            label_map[name] = int(label.get("id", 0))
            if name in POLELO_LABELS:
                label_map[name] = int(label.get("id", 0))

        for name, meta in POLELO_LABELS.items():
            if name in label_map:
                continue
            created = await self.create_label(name, meta["color"], meta["description"])
            label_map[name] = int(created.get("id", 0))
        return label_map

    async def list_labels(self) -> list[dict]:
        resp = await self._client.get(self._repo_path("/labels"))
        self._raise_for_status(resp)
        return resp.json()

    async def create_label(self, name: str, color: str, description: str) -> dict:
        resp = await self._client.post(
            self._repo_path("/labels"),
            json={"name": name, "color": color, "description": description},
        )
        self._raise_for_status(resp)
        return resp.json()

    # -- Issues -----------------------------------------------------------

    async def create_issue(
        self,
        title: str,
        body: str,
        labels: list[int] | None = None,
    ) -> dict:
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        resp = await self._client.post(self._repo_path("/issues"), json=payload)
        self._raise_for_status(resp)
        return resp.json()

    async def get_issue(self, issue_number: int) -> dict:
        resp = await self._client.get(self._repo_path(f"/issues/{issue_number}"))
        self._raise_for_status(resp)
        return resp.json()

    async def search_issues(
        self,
        query: str,
        state: str = "all",
        limit: int = 10,
    ) -> list[dict]:
        """Search issues in the configured repository (title + body)."""
        params: dict[str, Any] = {"q": query, "state": state, "limit": limit}
        resp = await self._client.get(self._repo_path("/issues/search"), params=params)
        self._raise_for_status(resp)
        data = resp.json()
        if isinstance(data, list):
            return data
        return data.get("issues", []) if isinstance(data, dict) else []

    async def add_labels(self, issue_number: int, label_ids: list[int]) -> list[dict]:
        resp = await self._client.post(
            self._repo_path(f"/issues/{issue_number}/labels"),
            json={"labels": label_ids},
        )
        self._raise_for_status(resp)
        return resp.json()

    async def remove_label(self, issue_number: int, label_id: int) -> None:
        resp = await self._client.delete(
            self._repo_path(f"/issues/{issue_number}/labels/{label_id}")
        )
        self._raise_for_status(resp)

    async def replace_labels(
        self,
        issue_number: int,
        desired: set[str],
        label_map: dict[str, int],
    ) -> None:
        """Idempotently replace the Polelo-managed labels on an issue.

        Adds any missing desired labels and removes Polelo labels no longer
        wanted. Never duplicates; labels outside the Polelo set are untouched.
        """
        issue = await self.get_issue(issue_number)
        current_names = {label.get("name") for label in issue.get("labels", []) if label.get("name")}

        for name in desired - current_names:
            if name in label_map:
                await self.add_labels(issue_number, [label_map[name]])

        for name in current_names - desired:
            if name in label_map:
                await self.remove_label(issue_number, label_map[name])

    async def reopen_issue(self, issue_number: int) -> dict:
        resp = await self._client.patch(
            self._repo_path(f"/issues/{issue_number}"),
            json={"state": "open"},
        )
        self._raise_for_status(resp)
        return resp.json()

    # -- Comments ---------------------------------------------------------

    async def list_comments(self, issue_number: int) -> list[dict]:
        resp = await self._client.get(self._repo_path(f"/issues/{issue_number}/comments"))
        self._raise_for_status(resp)
        return resp.json()

    async def post_comment(self, issue_number: int, body: str) -> dict:
        resp = await self._client.post(
            self._repo_path(f"/issues/{issue_number}/comments"),
            json={"body": body},
        )
        self._raise_for_status(resp)
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()
