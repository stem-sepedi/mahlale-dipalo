"""Standalone verification of Moodle webhook HMAC signing (no DB required).

Run: python3 -m tests.moodle_webhook_signature_check
"""

import hashlib
import hmac
import json
import os
import time

from src.api.routes.moodle_webhooks import (
    _compute_signature,
    _valid_secrets,
)


def test_signature_roundtrip():
    os.environ["MoodleWebhookSecret"] = "test-wh-secret"
    body = json.dumps({"event_type": "enrolment", "course_id": 2, "user_id": 10, "instance_url": "https://moodle.test"}).encode()
    ts = str(int(time.time()))

    sig = _compute_signature(body, "test-wh-secret", ts)
    assert len(sig) == 64

    # Recompute independently the way the server does
    message = f"{ts}.{body.decode('utf-8')}"
    expected = hmac.new(b"test-wh-secret", message.encode(), hashlib.sha256).hexdigest()
    assert hmac.compare_digest(sig, expected)

    assert _valid_secrets() == ["test-wh-secret"]


def test_signature_changes_with_secret():
    body = b'{"a": 1}'
    ts = "1700000000"
    s1 = _compute_signature(body, "secret-a", ts)
    s2 = _compute_signature(body, "secret-b", ts)
    assert s1 != s2


if __name__ == "__main__":
    test_signature_roundtrip()
    test_signature_changes_with_secret()
    print("Moodle webhook signature checks passed.")
