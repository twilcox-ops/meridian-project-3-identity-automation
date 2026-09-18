"""Severity-ranked HTML security posture report: runs all 7 Part A audit
checks and renders one HTML file, grouped CRITICAL / WARNING / INFO per
the finding-to-tier mapping in DECISIONS.md.

Two things aren't a direct 1:1 with a single check's output, per that
mapping:

  * "No MFA" splits CRITICAL/WARNING by whether the user also holds a
    privileged directory role -- cross-referenced here by Graph object id
    between users_without_mfa() and privileged_role_holders().
  * "SP credential" splits CRITICAL/WARNING by whether endDateTime has
    already passed, not just whether it's within the 30-day window --
    expiring_sp_credentials() already includes both, this just tells them
    apart by comparing endDateTime to now.

Privileged role holders and guest accounts are also each listed in full as
INFO rows (DECISIONS.md marks both "(informational)").
"""
import argparse
import html
import logging
from datetime import datetime, timezone

from audit_devices import flagged_devices
from audit_guests import guest_accounts
from audit_mfa import users_without_mfa
from audit_ownerless_groups import ownerless_groups
from audit_privileged_roles import privileged_role_holders
from audit_sp_creds import expiring_sp_credentials
from audit_stale_licensed import stale_licensed_accounts
from graph_client import GraphClient
from mailer import send_report_email

log = logging.getLogger("build_report")

TIER_ORDER = ["CRITICAL", "WARNING", "INFO"]
TIER_COLOR = {"CRITICAL": "#b91c1c", "WARNING": "#b45309", "INFO": "#1e40af"}


def collect_findings(client: GraphClient) -> list[dict]:
    """Run all 7 audit checks and return findings tagged per DECISIONS.md's tier mapping."""
    findings = []

    role_holders = list(privileged_role_holders(client))
    privileged_ids = {member.get("id") for _, member in role_holders}
    for role, member in role_holders:
        findings.append({
            "tier": "INFO",
            "category": "Privileged role holder",
            "identity": member.get("userPrincipalName") or member.get("displayName") or member.get("id"),
            "detail": f"role: {role.get('displayName')}",
        })

    for record in users_without_mfa(client):
        privileged = record.get("id") in privileged_ids
        findings.append({
            "tier": "CRITICAL" if privileged else "WARNING",
            "category": "No MFA registered" + (" (privileged role)" if privileged else ""),
            "identity": record.get("userPrincipalName"),
            "detail": record.get("userDisplayName") or "",
        })

    for record in stale_licensed_accounts(client):
        last_sign_in = (record.get("signInActivity") or {}).get("lastSignInDateTime") or "never"
        findings.append({
            "tier": "WARNING",
            "category": "Stale + licensed account",
            "identity": record.get("userPrincipalName"),
            "detail": f"last sign-in: {last_sign_in}",
        })

    for group in ownerless_groups(client):
        findings.append({
            "tier": "WARNING",
            "category": "Ownerless group",
            "identity": group.get("displayName"),
            "detail": group.get("id") or "",
        })

    now = datetime.now(timezone.utc)
    for sp, cred, kind in expiring_sp_credentials(client):
        end_date = datetime.fromisoformat(cred["endDateTime"].replace("Z", "+00:00"))
        expired = end_date <= now
        findings.append({
            "tier": "CRITICAL" if expired else "WARNING",
            "category": "SP credential " + ("expired" if expired else "expiring within 30 days"),
            "identity": sp.get("displayName"),
            "detail": f"{kind} ends {cred.get('endDateTime')}",
        })

    for record in guest_accounts(client):
        findings.append({
            "tier": "INFO",
            "category": "Guest account",
            "identity": record.get("userPrincipalName"),
            "detail": f"tenure: {record.get('tenure_days')}d, state: {record.get('externalUserState')}",
        })

    for record in flagged_devices(client):
        findings.append({
            "tier": "WARNING",
            "category": "Non-compliant/stale device",
            "identity": record.get("displayName"),
            "detail": f"compliant={record.get('isCompliant')}, last check-in={record.get('approximateLastSignInDateTime')}",
        })

    return findings


def render_html(findings: list[dict]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    counts = {tier: sum(1 for f in findings if f["tier"] == tier) for tier in TIER_ORDER}

    sections = []
    for tier in TIER_ORDER:
        tier_findings = sorted(
            (f for f in findings if f["tier"] == tier),
            key=lambda f: (f["category"], f["identity"] or ""),
        )
        rows = "".join(
            f"<tr><td>{html.escape(f['category'])}</td>"
            f"<td>{html.escape(str(f['identity']))}</td>"
            f"<td>{html.escape(str(f['detail']))}</td></tr>"
            for f in tier_findings
        ) or "<tr><td colspan=\"3\" class=\"empty\">No findings</td></tr>"
        sections.append(f"""
        <section>
          <h2 style="color:{TIER_COLOR[tier]}">{tier} ({counts[tier]})</h2>
          <table>
            <thead><tr><th>Category</th><th>Identity / Resource</th><th>Detail</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </section>""")

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Identity Security Posture Report</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #111; }}
  h1 {{ margin-bottom: 0.25rem; }}
  .generated {{ color: #555; margin-top: 0; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 2rem; }}
  th, td {{ border: 1px solid #ddd; padding: 0.4rem 0.6rem; text-align: left; font-size: 0.9rem; }}
  th {{ background: #f5f5f5; }}
  .empty {{ color: #777; font-style: italic; }}
</style>
</head>
<body>
  <h1>Identity Security Posture Report</h1>
  <p class="generated">Generated {generated_at}</p>
  {"".join(sections)}
</body>
</html>
"""


def _demo(output_path: str):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = GraphClient()
    findings = collect_findings(client)
    counts = {tier: sum(1 for f in findings if f["tier"] == tier) for tier in TIER_ORDER}
    html_report = render_html(findings)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_report)
    log.info("wrote %s: %d CRITICAL, %d WARNING, %d INFO", output_path, *counts.values())

    subject = f"Identity posture report: {counts['CRITICAL']} CRITICAL, {counts['WARNING']} WARNING, {counts['INFO']} INFO"
    send_report_email(client, subject, html_report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all 7 audit checks and write a severity-ranked HTML report.")
    parser.add_argument("--output", default="report.html", help="path to write the HTML report to")
    args = parser.parse_args()
    _demo(args.output)
