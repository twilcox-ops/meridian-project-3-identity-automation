"""Self-check for the report's non-trivial logic: the two spots where a
single check's raw output must be split into two tiers by cross-referencing
or comparing against "now" (No-MFA-but-privileged -> CRITICAL, SP cred
already-expired -> CRITICAL), plus render_html's CRITICAL/WARNING/INFO
ordering. No network -- one FakeSession queue drives all 7 underlying
Graph calls in the exact order collect_findings() makes them.
Run: python -m unittest test_build_report.py -v
"""
import unittest
from datetime import datetime, timedelta, timezone

from build_report import collect_findings, render_html
from graph_client import GraphClient
from test_graph_client import FakeCredential, FakeResponse, FakeSession


def _iso(delta_days):
    return (datetime.now(timezone.utc) + timedelta(days=delta_days)).isoformat().replace("+00:00", "Z")


def _fake_client():
    roles_page = FakeResponse(200, {"value": [{"id": "role-1", "displayName": "Global Administrator"}]})
    members_page = FakeResponse(200, {"value": [{"id": "u-priv", "userPrincipalName": "priv@x.com"}]})
    mfa_page = FakeResponse(200, {"value": [
        {"id": "u-priv", "userPrincipalName": "priv@x.com", "userDisplayName": "Priv User", "isMfaRegistered": False},
        {"id": "u-reg", "userPrincipalName": "reg@x.com", "userDisplayName": "Regular User", "isMfaRegistered": False},
        {"id": "u-ok", "userPrincipalName": "ok@x.com", "isMfaRegistered": True},
    ]})
    stale_page = FakeResponse(200, {"value": [
        {"userPrincipalName": "stale@x.com", "assignedLicenses": [{"skuId": "a"}],
         "signInActivity": {"lastSignInDateTime": "2020-01-01T00:00:00Z"}},
    ]})
    groups_page = FakeResponse(200, {"value": [{"id": "g1", "displayName": "No Owner Group"}]})
    owners_page = FakeResponse(200, {"value": []})
    sp_page = FakeResponse(200, {"value": [
        {"displayName": "sp-expired", "keyCredentials": [{"endDateTime": _iso(-5)}], "passwordCredentials": []},
        {"displayName": "sp-nearing", "keyCredentials": [], "passwordCredentials": [{"endDateTime": _iso(10)}]},
    ]})
    guests_page = FakeResponse(200, {"value": [
        {"userPrincipalName": "guest@x.com", "createdDateTime": _iso(-400), "externalUserState": "Accepted"},
    ]})
    devices_page = FakeResponse(200, {"value": [
        {"displayName": "bad-device", "isCompliant": False, "approximateLastSignInDateTime": _iso(-5)},
    ]})

    session = FakeSession([
        roles_page, members_page, mfa_page, stale_page,
        groups_page, owners_page, sp_page, guests_page, devices_page,
    ])
    return GraphClient(credential=FakeCredential(), session=session)


class CollectFindingsTests(unittest.TestCase):
    def test_no_mfa_privileged_user_escalates_to_critical(self):
        findings = collect_findings(_fake_client())
        priv = next(f for f in findings if f["category"].startswith("No MFA") and f["identity"] == "priv@x.com")
        reg = next(f for f in findings if f["category"].startswith("No MFA") and f["identity"] == "reg@x.com")

        self.assertEqual(priv["tier"], "CRITICAL")
        self.assertEqual(reg["tier"], "WARNING")

    def test_sp_credential_already_expired_escalates_to_critical(self):
        findings = collect_findings(_fake_client())
        expired = next(f for f in findings if f["identity"] == "sp-expired")
        nearing = next(f for f in findings if f["identity"] == "sp-nearing")

        self.assertEqual(expired["tier"], "CRITICAL")
        self.assertEqual(nearing["tier"], "WARNING")

    def test_informational_findings_are_info_tier(self):
        findings = collect_findings(_fake_client())
        role_holder = next(f for f in findings if f["category"] == "Privileged role holder")
        guest = next(f for f in findings if f["category"] == "Guest account")

        self.assertEqual(role_holder["tier"], "INFO")
        self.assertEqual(guest["tier"], "INFO")

    def test_finding_count_matches_all_7_checks(self):
        findings = collect_findings(_fake_client())
        # 1 privileged role holder + 2 no-MFA + 1 stale-licensed + 1 ownerless
        # group + 2 SP creds + 1 guest + 1 device = 9
        self.assertEqual(len(findings), 9)


class RenderHtmlTests(unittest.TestCase):
    def test_sections_appear_in_critical_warning_info_order(self):
        html_out = render_html(collect_findings(_fake_client()))

        self.assertLess(html_out.index(">CRITICAL"), html_out.index(">WARNING"))
        self.assertLess(html_out.index(">WARNING"), html_out.index(">INFO"))

    def test_empty_tier_renders_no_findings(self):
        html_out = render_html([{"tier": "WARNING", "category": "x", "identity": "y", "detail": "z"}])

        self.assertIn("No findings", html_out)  # CRITICAL and INFO are both empty


if __name__ == "__main__":
    unittest.main()
