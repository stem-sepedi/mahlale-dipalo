"""Tests for M10 question triage — Forgejo client + triage decision logic.

The Forgejo/Gitea REST API is mocked with httpx.MockTransport so no live Forgejo
instance or database is required.
"""

import json

import httpx
import pytest

from src.services.forgejo_client import POLELO_LABELS, ForgejoClient
from src.services.question_engine import QuestionAnswerEngine, _parse_json
from src.services.question_triage import triage_question


class FakeForgejo:
    """Stateful fake of the Forgejo REST API surfaces used by the triage flow."""

    def __init__(self):
        self.labels: dict[str, dict] = {}
        self.issues: dict[int, dict] = {}
        self.comments: dict[int, list[dict]] = {}
        self.next_issue = 1
        self.next_label = 1
        self.searches: list[tuple[str, str]] = []

    # -- helpers for tests ------------------------------------------------

    def add_issue(self, number: int, title: str, labels: list[str]) -> dict:
        issue = {
            "number": number,
            "title": title,
            "body": "",
            "labels": [{"id": self._label_id(name), "name": name} for name in labels],
        }
        self.issues[number] = issue
        return issue

    def _label_id(self, name: str) -> int:
        if name not in self.labels:
            self.labels[name] = {"id": self.next_label, "name": name}
            self.next_label += 1
        return self.labels[name]["id"]

    # -- fake HTTP handler ------------------------------------------------

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        method = request.method

        if url.endswith("/repos/o/r/labels") and method == "GET":
            return httpx.Response(200, json=list(self.labels.values()))

        if url.endswith("/repos/o/r/labels") and method == "POST":
            data = json.loads(request.content or b"{}")
            name = data["name"]
            self._label_id(name)
            return httpx.Response(201, json=self.labels[name])

        if url.endswith("/repos/o/r/issues") and method == "POST":
            data = json.loads(request.content or b"{}")
            labels = data.get("labels", [])
            issue = self.add_issue(
                self.next_issue, data["title"], [self._name_for_id(label_id) for label_id in labels]
            )
            self.next_issue += 1
            return httpx.Response(201, json=issue)

        if "/issues/search" in url and method == "GET":
            params = dict(request.url.params)
            self.searches.append((params.get("q", ""), params.get("state", "all")))
            tokens = [w for w in params.get("q", "").lower().split() if len(w) > 3]
            matches = [
                i for i in self.issues.values()
                if any(t in i["title"].lower() or t in i["body"].lower() for t in tokens)
            ]
            return httpx.Response(200, json=matches)

        parts = url.split("/")
        if "issues" in parts and "comments" in parts and method == "POST":
            index = int(parts[parts.index("issues") + 1])
            data = json.loads(request.content or b"{}")
            comment = {"id": 1, "body": data["body"]}
            self.comments.setdefault(index, []).append(comment)
            return httpx.Response(201, json=comment)

        if "issues" in parts and "comments" in parts and method == "GET":
            index = int(parts[parts.index("issues") + 1])
            return httpx.Response(200, json=self.comments.get(index, []))

        # GET /repos/o/r/issues/{index}
        if "issues" in parts and method == "GET":
            index = int(parts[parts.index("issues") + 1])
            return httpx.Response(200, json=self.issues.get(index, {}))

        # POST /repos/o/r/issues/{index}/labels
        if url.endswith("/labels") and method == "POST":
            index = int(parts[parts.index("issues") + 1])
            data = json.loads(request.content or b"{}")
            current = self.issues[index]
            have = {label["name"] for label in current["labels"]}
            for lid in data.get("labels", []):
                name = self._name_for_id(lid)
                if name not in have:
                    current["labels"].append({"id": lid, "name": name})
                    have.add(name)
            return httpx.Response(200, json=current["labels"])

        if method == "DELETE" and url.endswith("/labels/" + url.split("/")[-1]) and "/labels/" in url:
            index = int(parts[parts.index("issues") + 1])
            label_id = int(url.split("/")[-1])
            current = self.issues[index]
            current["labels"] = [label for label in current["labels"] if label["id"] != label_id]
            return httpx.Response(204)

        # PATCH issue (reopen)
        if method == "PATCH" and "issues" in parts and len(parts) > 1:
            index = int(parts[parts.index("issues") + 1])
            data = json.loads(request.content or b"{}")
            self.issues[index].update(data)
            return httpx.Response(200, json=self.issues[index])

        raise AssertionError(f"Unhandled {method} {url}")

    def _name_for_id(self, label_id: int) -> str:
        for name, label in self.labels.items():
            if label["id"] == label_id:
                return name
        return f"unknown-{label_id}"

@pytest.fixture
def fake() -> FakeForgejo:
    return FakeForgejo()


@pytest.fixture
def client(fake: FakeForgejo) -> ForgejoClient:
    transport = httpx.MockTransport(fake)
    return ForgejoClient(
        base_url="https://forgejo.example.test",
        token="tok",
        owner="o",
        repo="r",
        client=httpx.AsyncClient(
            transport=transport, base_url="https://forgejo.example.test/api/v1"
        ),
    )


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_ensure_labels_creates_missing_labels(client: ForgejoClient, fake: FakeForgejo):
    label_map = await client.ensure_labels()
    assert set(label_map) == set(POLELO_LABELS)
    # Idempotent — calling again does not duplicate
    label_map2 = await client.ensure_labels()
    assert label_map2 == label_map
    assert fake.next_label - 1 == len(POLELO_LABELS)


@pytest.mark.asyncio
async def test_replace_labels_adds_and_removes_without_duplicating(client: ForgejoClient, fake: FakeForgejo):
    await client.ensure_labels()
    label_map = {
        name: fake.labels[name]["id"] for name in POLELO_LABELS
    }
    fake.add_issue(1, "What is photosynthesis?", ["LLM_BACKLOG"])

    await client.replace_labels(1, {"LLM_WIP"}, label_map)
    names = {label["name"] for label in fake.issues[1]["labels"]}
    assert names == {"LLM_WIP"}

    await client.replace_labels(1, {"LLM_DONE", "HUMAN_BACKLOG"}, label_map)
    names = {label["name"] for label in fake.issues[1]["labels"]}
    assert names == {"LLM_DONE", "HUMAN_BACKLOG"}

    await client.replace_labels(1, {"LLM_DONE", "HUMAN_BACKLOG"}, label_map)
    names = {label["name"] for label in fake.issues[1]["labels"]}
    assert names == {"LLM_DONE", "HUMAN_BACKLOG"}


@pytest.mark.asyncio
async def test_triage_new_when_no_candidates(client: ForgejoClient, fake: FakeForgejo):
    fake.add_issue(1, "What is photosynthesis?", ["LLM_BACKLOG"])
    result = await triage_question(client, 1, "What is photosynthesis?")
    assert result["decision"] == "new"
    assert result["matching_issue_number"] is None


@pytest.mark.asyncio
async def test_triage_reuses_answered_question(client: ForgejoClient, fake: FakeForgejo):
    fake.add_issue(1, "What is photosynthesis?", ["LLM_BACKLOG"])
    fake.add_issue(7, "What is photosynthesis?", ["LLM_DONE", "HUMAN_VERIFIED"])
    fake.comments[7] = [{"id": 1, "body": "Photosynthesis ke tshepetso ya go dira dijo."}]

    result = await triage_question(client, 1, "What is photosynthesis?")
    assert result["decision"] == "answered"
    assert result["matching_issue_number"] == 7
    assert result["answer"] == "Photosynthesis ke tshepetso ya go dira dijo."


@pytest.mark.asyncio
async def test_triage_marks_similar_unanswered(client: ForgejoClient, fake: FakeForgejo):
    fake.add_issue(1, "What is photosynthesis?", ["LLM_BACKLOG"])
    fake.add_issue(9, "Explain photosynthesis for grade 8", ["LLM_BACKLOG"])

    result = await triage_question(client, 1, "What is photosynthesis?")
    assert result["decision"] == "similar"
    assert result["matching_issue_number"] == 9
    assert result["answer"] is None


@pytest.mark.asyncio
async def test_triage_ignores_own_issue(client: ForgejoClient, fake: FakeForgejo):
    fake.add_issue(3, "What is gravity?", ["LLM_BACKLOG"])
    result = await triage_question(client, 3, "What is gravity?")
    assert result["decision"] == "new"
    assert result["matching_issue_number"] is None


@pytest.mark.asyncio
async def test_triage_survives_search_failure():
    async def _boom(request):
        raise httpx.RequestError("connection refused", request=request)

    transport = httpx.MockTransport(_boom)
    client = ForgejoClient(
        base_url="https://forgejo.example.test", token="tok", owner="o", repo="r",
        client=httpx.AsyncClient(transport=transport, base_url="https://forgejo.example.test/api/v1"),
    )
    result = await triage_question(client, 1, "anything")
    assert result["decision"] == "new"
    assert result["answer"] is None


@pytest.mark.asyncio
async def test_question_engine_parses_answer_json():
    class FakeOllama:
        async def generate(self, prompt, **kwargs):
            return '{"answer_sep": "Karabo ka Sepedi.", "confidence_score": 0.92}'

    engine = QuestionAnswerEngine(ollama=FakeOllama())
    result = await engine.answer("What is a cell?", grade=8, subject="Biology")
    assert result["answer_sep"] == "Karabo ka Sepedi."
    assert result["confidence_score"] == 0.92


def test_parse_json_handles_markdown_fences():
    raw = '```json\n{"answer_sep": "x", "confidence_score": 0.5}\n```'
    assert _parse_json(raw, fallback={}) == {"answer_sep": "x", "confidence_score": 0.5}


def test_parse_json_falls_back_on_garbage():
    assert _parse_json("not json at all", {"answer_sep": "", "confidence_score": 0.0}) == {
        "answer_sep": "",
        "confidence_score": 0.0,
    }
