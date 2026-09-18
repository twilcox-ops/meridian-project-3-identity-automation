"""Self-check for the MFA filter: records with isMfaRegistered falsy (False
or missing) must be returned; records with it True must not.

Run: python -m unittest test_audit_mfa.py -v
"""
import unittest

from audit_mfa import users_without_mfa
from graph_client import GraphClient
from test_graph_client import FakeCredential, FakeResponse, FakeSession


class MfaFilterTests(unittest.TestCase):
    def test_filters_to_users_without_mfa_registered(self):
        page = FakeResponse(200, {"value": [
            {"userPrincipalName": "a@x.com", "isMfaRegistered": True},
            {"userPrincipalName": "b@x.com", "isMfaRegistered": False},
            {"userPrincipalName": "c@x.com"},  # field absent -> treated as not registered
        ]})
        session = FakeSession([page])
        client = GraphClient(credential=FakeCredential(), session=session)

        result = list(users_without_mfa(client))

        self.assertEqual([r["userPrincipalName"] for r in result], ["b@x.com", "c@x.com"])


if __name__ == "__main__":
    unittest.main()
