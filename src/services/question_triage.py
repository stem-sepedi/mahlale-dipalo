"""Triage logic for M10 — decide new / similar / answered before the LLM runs.

Queries the configured Forgejo repository for existing questions before an LLM
call is dispatched, so previously-answered questions are reused instead of
re-generated.
"""

import logging
import re

logger = logging.getLogger(__name__)

# An issue is considered already answered if it carries either of these labels.
ANSWERED_LABELS = frozenset({"LLM_DONE", "HUMAN_VERIFIED"})


async def triage_question(
    client,
    issue_number: int,
    question_text: str,
    limit: int = 5,
) -> dict:
    """Search Forgejo for existing questions about the same topic.

    Returns a dict with the decision:
      - new:       no prior question found -> proceed to LLM
      - similar:   similar issue exists (unanswered) -> add LLM_SIMILAR
      - answered:  prior issue already answered -> reuse the answer
    """
    query = " ".join(re.findall(r"[A-Za-z0-9']+", question_text)[:8])
    try:
        candidates = await client.search_issues(query, state="all", limit=limit)
    except Exception as exc:
        logger.warning("Forgejo triage search failed: %s", exc)
        return {"decision": "new", "matching_issue_number": None, "answer": None}

    # 1. Reuse an existing answer if any candidate is already answered.
    for candidate in candidates:
        index = int(candidate.get("number", 0))
        if index == issue_number:
            continue
        names = {label.get("name") for label in candidate.get("labels", [])}
        if names & ANSWERED_LABELS:
            answer = None
            try:
                comments = await client.list_comments(index)
                if comments:
                    answer = comments[-1].get("body")
            except Exception as exc:
                logger.warning("Failed to fetch comments for issue %s: %s", index, exc)
            return {"decision": "answered", "matching_issue_number": index, "answer": answer}

    # 2. Otherwise note the closest similar (unanswered) question.
    for candidate in candidates:
        index = int(candidate.get("number", 0))
        if index == issue_number:
            continue
        return {"decision": "similar", "matching_issue_number": index, "answer": None}

    return {"decision": "new", "matching_issue_number": None, "answer": None}
