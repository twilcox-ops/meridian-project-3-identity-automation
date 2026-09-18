"""Self-check: only credentials expiring within 30 days (or already expired)
are flagged; both keyCredentials and passwordCredentials are checked.
Run: python -m unittest test_audit_sp_creds.py -v
"""
import unittest
from datetime import datetime, timedelta, timezone

from audit_sp_creds import expiring_sp_credentials
from graph_client import GraphClient
from test_graph_client import FakeCredential, FakeResponse, FakeSession


def _iso(days_from_now):
    return (datetime.now(timezone.utc) + timedelta(days=days_from_now)).isoformat().replace("+00:00", "Z")


class ExpiringSpCredTests(unittest.TestCase):
    def test_flags_near_and_past_expiry_across_both_cred_types(self):
        page = FakeResponse(200, {"value": [
            {"displayName": "sp-safe", "keyCredentials": [{"endDateTime": _iso(90)}], "passwordCredentials": []},
            {"displayName": "sp-nearing", "keyCredentials": [{"endDateTime": _iso(10)}], "passwordCredentials": []},
            {"displayName": "sp-expired", "keyCredentials": [], "passwordCredentials": [{"endDateTime": _iso(-5)}]},
        ]})
        session = FakeSession([page])
        client = GraphClient(credential=FakeCredential(), session=session)

        result = list(expiring_sp_credentials(client))

        self.assertEqual([sp["displayName"] for sp, _, _ in result], ["sp-nearing", "sp-expired"])
        self.assertEqual([kind for _, _, kind in result], ["keyCredentials", "passwordCredentials"])


if __name__ == "__main__":
    unittest.main()
