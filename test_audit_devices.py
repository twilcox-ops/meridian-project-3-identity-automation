"""Self-check: devices are flagged if non-compliant, unseen for 90+ days,
or never seen; compliant+recent devices are not. Run:
python -m unittest test_audit_devices.py -v
"""
import unittest
from datetime import datetime, timedelta, timezone

from audit_devices import flagged_devices
from graph_client import GraphClient
from test_graph_client import FakeCredential, FakeResponse, FakeSession


def _iso(days_ago):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")


class FlaggedDeviceTests(unittest.TestCase):
    def test_flags_noncompliant_and_stale_only(self):
        page = FakeResponse(200, {"value": [
            {"displayName": "healthy", "isCompliant": True, "approximateLastSignInDateTime": _iso(5)},
            {"displayName": "noncompliant", "isCompliant": False, "approximateLastSignInDateTime": _iso(5)},
            {"displayName": "stale", "isCompliant": True, "approximateLastSignInDateTime": _iso(200)},
            {"displayName": "never-checked-in", "isCompliant": True, "approximateLastSignInDateTime": None},
        ]})
        session = FakeSession([page])
        client = GraphClient(credential=FakeCredential(), session=session)

        result = list(flagged_devices(client))

        self.assertEqual(
            [d["displayName"] for d in result],
            ["noncompliant", "stale", "never-checked-in"],
        )


if __name__ == "__main__":
    unittest.main()
