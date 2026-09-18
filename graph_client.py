"""Minimal Graph API client: pagination + 429 throttling, nothing else.

Deliberately thin — a wrapper around `requests`, not a reimplementation of
the SDK. Two things it must get right per the project's technical
requirements:

  * follow @odata.nextLink until it's absent (pagination)
  * on 429, sleep for exactly what Retry-After says — no fixed sleep,
    no immediate retry — then retry the same request (throttling)
"""
import argparse
import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

import graph_auth

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
FALLBACK_RETRY_SECONDS = 5  # only used if Graph sends a 429 with no usable Retry-After
MAX_RETRIES = 5

log = logging.getLogger("graph_client")


def _parse_retry_after(header_value):
    """Retry-After is either delta-seconds or an HTTP-date (RFC 7231)."""
    if not header_value:
        return None
    header_value = header_value.strip()
    if header_value.isdigit():
        return int(header_value)
    try:
        dt = parsedate_to_datetime(header_value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, (dt - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return None


class GraphClient:
    def __init__(self, credential=None, session=None):
        self.credential = credential or graph_auth.get_graph_credential()
        self.session = session or requests.Session()

    def _access_token(self) -> str:
        return self.credential.get_token("https://graph.microsoft.com/.default").token

    def _request(self, method: str, url: str, **kwargs) -> dict:
        """One HTTP call, retrying on 429 by honoring Retry-After. Shared by
        get() and post() so throttling is handled in exactly one place."""
        if not url.startswith("http"):
            url = f"{GRAPH_BASE}{url}"

        for attempt in range(1, MAX_RETRIES + 1):
            headers = {"Authorization": f"Bearer {self._access_token()}"}
            response = getattr(self.session, method)(url, headers=headers, **kwargs)

            if response.status_code == 429:
                wait = _parse_retry_after(response.headers.get("Retry-After"))
                if wait is None:
                    wait = FALLBACK_RETRY_SECONDS
                    log.warning(
                        "429 from %s with no usable Retry-After header; falling back to %ss",
                        url, wait,
                    )
                else:
                    log.warning("429 from %s; honoring Retry-After: sleeping %ss", url, wait)
                time.sleep(wait)
                continue

            if not response.ok:
                log.error("HTTP %s from %s: %s", response.status_code, url, response.text)
            response.raise_for_status()
            return response.json() if response.text else {}

        raise RuntimeError(f"Exceeded {MAX_RETRIES} retries against {url} (still throttled)")

    def get(self, url: str, params: dict | None = None) -> dict:
        """GET one page, retrying on 429 by honoring Retry-After."""
        return self._request("get", url, params=params)

    def post(self, url: str, json: dict | None = None) -> dict:
        """POST (e.g. sendMail), retrying on 429 by honoring Retry-After.
        Graph returns 202 with no body for sendMail, hence the empty-body
        guard in _request()."""
        return self._request("post", url, json=json)

    def get_paginated(self, url: str, params: dict | None = None):
        """Yield every item across all pages, following @odata.nextLink."""
        next_url, next_params = url, params
        page = 1
        while next_url:
            data = self.get(next_url, params=next_params)
            items = data.get("value", [])
            log.info("page %d: %d items from %s", page, len(items), next_url)
            yield from items
            next_url = data.get("@odata.nextLink")
            next_params = None  # nextLink already has all query params baked in
            page += 1


def _demo(top: int):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = GraphClient()
    count = 0
    for user in client.get_paginated("/users", params={"$top": top, "$select": "id,displayName"}):
        count += 1
        log.info("user: %s (%s)", user.get("displayName"), user.get("id"))
    log.info("total users fetched: %d", count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List all users, paginating with the given page size.")
    parser.add_argument("--top", type=int, default=5, help="$top page size (small value forces paging)")
    args = parser.parse_args()
    _demo(args.top)
