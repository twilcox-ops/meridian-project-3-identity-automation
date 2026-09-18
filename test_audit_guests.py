"""Self-check: tenure_days is computed correctly relative to createdDateTime.
Run: python -m unittest test_audit_guests.py -v
"""
import unittest
from datetime import datetime, timedelta, timezone

from audit_guests import guest_accounts
from graph_client import GraphClient
from test_graph_client import FakeCredential, FakeResponse, FakeSession


class GuestTenureTests(unittest.TestCase):
    def test_computes_tenure_days(self):
        created = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat().replace("+00:00", "Z")
        page = FakeResponse(200, {"value": [
            {"userPrincipalName": "guest@x.com", "createdDateTime": created, "externalUserState": "Accepted"},
        ]})
        session = FakeSession([page])
        client = GraphClient(credential=FakeCredential(), session=session)

        result = list(guest_accounts(client))

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]["tenure_days"], 400, delta=1)


if __name__ == "__main__":
    unittest.main()
