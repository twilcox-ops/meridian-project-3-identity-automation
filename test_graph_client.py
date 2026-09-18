"""Self-check for the two pieces of non-trivial logic in graph_client.py:
pagination via @odata.nextLink, and 429 handling via Retry-After.
No network, no real credential — fakes stand in for both.

Run: python -m unittest test_graph_client.py -v
"""
import time
import unittest
from unittest.mock import patch

from graph_client import GraphClient, _parse_retry_after


class FakeToken:
    token = "fake-token"


class FakeCredential:
    def get_token(self, *_scopes):
        return FakeToken()


class FakeResponse:
    def __init__(self, status_code, json_data=None, headers=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}
        self.text = text or str(json_data or "")

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400 and self.status_code != 429:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Returns queued responses in order, one per .get() call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def get(self, url, headers=None, params=None):
        self.calls.append(url)
        return self._responses.pop(0)


class PaginationTests(unittest.TestCase):
    def test_follows_next_link_until_absent(self):
        page1 = FakeResponse(200, {
            "value": [{"id": "1"}, {"id": "2"}],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/users?$skiptoken=abc",
        })
        page2 = FakeResponse(200, {"value": [{"id": "3"}]})
        session = FakeSession([page1, page2])

        client = GraphClient(credential=FakeCredential(), session=session)
        items = list(client.get_paginated("/users", params={"$top": 2}))

        self.assertEqual([i["id"] for i in items], ["1", "2", "3"])
        self.assertEqual(len(session.calls), 2)


class ThrottlingTests(unittest.TestCase):
    def test_retry_after_seconds_is_honored_not_a_fixed_sleep(self):
        throttled = FakeResponse(429, headers={"Retry-After": "17"})
        ok = FakeResponse(200, {"value": [{"id": "1"}]})
        session = FakeSession([throttled, ok])
        client = GraphClient(credential=FakeCredential(), session=session)

        with patch("graph_client.time.sleep") as mock_sleep:
            result = client.get("/users")

        mock_sleep.assert_called_once_with(17)
        self.assertEqual(result["value"][0]["id"], "1")

    def test_does_not_retry_immediately_without_sleeping(self):
        throttled = FakeResponse(429, headers={"Retry-After": "3"})
        ok = FakeResponse(200, {"value": []})
        session = FakeSession([throttled, ok])
        client = GraphClient(credential=FakeCredential(), session=session)

        real_sleep_calls = []
        with patch("graph_client.time.sleep", side_effect=lambda s: real_sleep_calls.append(s)):
            client.get("/users")

        self.assertEqual(real_sleep_calls, [3])

    def test_parses_http_date_retry_after(self):
        from email.utils import format_datetime
        from datetime import datetime, timezone, timedelta

        future = datetime.now(timezone.utc) + timedelta(seconds=10)
        header = format_datetime(future, usegmt=True)
        wait = _parse_retry_after(header)
        self.assertAlmostEqual(wait, 10, delta=1)

    def test_missing_header_falls_back_and_still_retries(self):
        throttled = FakeResponse(429, headers={})
        ok = FakeResponse(200, {"value": []})
        session = FakeSession([throttled, ok])
        client = GraphClient(credential=FakeCredential(), session=session)

        with patch("graph_client.time.sleep") as mock_sleep:
            client.get("/users")

        mock_sleep.assert_called_once_with(5)


if __name__ == "__main__":
    unittest.main()
