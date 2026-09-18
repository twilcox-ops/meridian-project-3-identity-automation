"""Self-check: only licensed users with no sign-in or a sign-in older than
90 days are flagged. Run: python -m unittest test_audit_stale_licensed.py -v
"""
import unittest

from audit_stale_licensed import stale_licensed_accounts
from graph_client import GraphClient
from test_graph_client import FakeCredential, FakeResponse, FakeSession


class StaleLicensedTests(unittest.TestCase):
    def test_filters_to_licensed_and_stale(self):
        page = FakeResponse(200, {"value": [
            {"userPrincipalName": "recent@x.com", "assignedLicenses": [{"skuId": "a"}],
             "signInActivity": {"lastSignInDateTime": "2026-09-01T00:00:00Z"}},
            {"userPrincipalName": "stale@x.com", "assignedLicenses": [{"skuId": "a"}],
             "signInActivity": {"lastSignInDateTime": "2020-01-01T00:00:00Z"}},
            {"userPrincipalName": "never-signed-in@x.com", "assignedLicenses": [{"skuId": "a"}],
             "signInActivity": {}},
            {"userPrincipalName": "unlicensed-stale@x.com", "assignedLicenses": [],
             "signInActivity": {"lastSignInDateTime": "2020-01-01T00:00:00Z"}},
        ]})
        session = FakeSession([page])
        client = GraphClient(credential=FakeCredential(), session=session)

        result = list(stale_licensed_accounts(client))

        self.assertEqual(
            [r["userPrincipalName"] for r in result],
            ["stale@x.com", "never-signed-in@x.com"],
        )


if __name__ == "__main__":
    unittest.main()
