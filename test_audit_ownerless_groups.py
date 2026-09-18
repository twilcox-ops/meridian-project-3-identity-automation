"""Self-check: groups with zero owners are flagged, groups with an owner
are not. Run: python -m unittest test_audit_ownerless_groups.py -v
"""
import unittest

from audit_ownerless_groups import ownerless_groups
from graph_client import GraphClient
from test_graph_client import FakeCredential, FakeResponse, FakeSession


class OwnerlessGroupTests(unittest.TestCase):
    def test_flags_only_groups_with_no_owners(self):
        groups_page = FakeResponse(200, {"value": [
            {"id": "g1", "displayName": "Has Owner"},
            {"id": "g2", "displayName": "No Owner"},
        ]})
        owners_g1 = FakeResponse(200, {"value": [{"id": "u1"}]})
        owners_g2 = FakeResponse(200, {"value": []})
        session = FakeSession([groups_page, owners_g1, owners_g2])
        client = GraphClient(credential=FakeCredential(), session=session)

        result = list(ownerless_groups(client))

        self.assertEqual([g["displayName"] for g in result], ["No Owner"])


if __name__ == "__main__":
    unittest.main()
