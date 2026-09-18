"""Self-check: yields one (role, member) pair per member of each activated
role. Run: python -m unittest test_audit_privileged_roles.py -v
"""
import unittest

from audit_privileged_roles import privileged_role_holders
from graph_client import GraphClient
from test_graph_client import FakeCredential, FakeResponse, FakeSession


class PrivilegedRoleTests(unittest.TestCase):
    def test_yields_role_member_pairs(self):
        roles_page = FakeResponse(200, {"value": [
            {"id": "role-1", "displayName": "Global Administrator"},
        ]})
        members_page = FakeResponse(200, {"value": [
            {"id": "u1", "userPrincipalName": "admin1@x.com"},
            {"id": "u2", "userPrincipalName": "admin2@x.com"},
        ]})
        session = FakeSession([roles_page, members_page])
        client = GraphClient(credential=FakeCredential(), session=session)

        result = list(privileged_role_holders(client))

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0]["displayName"], "Global Administrator")
        self.assertEqual([m["userPrincipalName"] for _, m in result], ["admin1@x.com", "admin2@x.com"])


if __name__ == "__main__":
    unittest.main()
