"""Audit check: groups with no owner.

Requires Group.Read.All (application) to list groups and read owners; a
widening specific to this check (DECISIONS.md rule). Granted and
admin-consented in Entra; not yet run against the real tenant.
"""
import argparse
import logging

from graph_client import GraphClient

log = logging.getLogger("audit_ownerless_groups")

GROUPS_PATH = "/groups"
SELECT = "id,displayName,mailEnabled,securityEnabled"


def ownerless_groups(client: GraphClient):
    """Yield group records that have zero owners."""
    for group in client.get_paginated(GROUPS_PATH, params={"$select": SELECT}):
        owners_path = f"/groups/{group['id']}/owners"
        if not any(client.get_paginated(owners_path, params={"$select": "id"})):
            yield group


def _demo():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = GraphClient()
    count = 0
    for group in ownerless_groups(client):
        count += 1
        log.info("ownerless group: %s (%s)", group.get("displayName"), group.get("id"))
    log.info("total ownerless groups: %d", count)


if __name__ == "__main__":
    argparse.ArgumentParser(description="List groups with no owner.").parse_args()
    _demo()
