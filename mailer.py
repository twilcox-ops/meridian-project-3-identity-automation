"""Email delivery for the HTML report, via Microsoft Graph sendMail.

Reuses Project 1's mailer pattern (project-1-scheduled-pipeline/pipeline.py:
send_digest_email): build a sendMail message dict, POST to
/users/{mailbox}/sendMail with saveToSentItems: false, and if the mailbox
env vars aren't set, just log and skip the send rather than fail the run --
the report should still be generated even when mail isn't configured.

Not reused as-is: Project 1 fetches its own token via a client-secret
client-credentials POST (get_graph_token()). This project already has a
cert-based, throttle-aware GraphClient (graph_client.py); reusing that
client's post() -- rather than copying Project 1's token fetch -- is the
same "reuse is the point" the project asks for, applied to auth+throttling
instead of duplicating it a second time.

Requires Mail.Send (application), scoped via Exchange Online RBAC for
Applications to GRAPH_SENDER_MAILBOX only -- the same non-tenant-wide
scoping Project 1 used (see its README: Test-ServicePrincipalAuthorization
confirms InScope=True for the intended mailbox, False for others).
NOT YET GRANTED in Entra/Exchange Online as of this build. Project 1's own
repo doesn't record the exact commands it ran for this (its README only
describes the pattern), so this is the standard Exchange Online cmdlet
sequence for that same pattern, not something copied from Project 1's
history:

  Connect-ExchangeOnline

  # ObjectId is the Entra ENTERPRISE APP's (service principal's) object id,
  # not the app registration's object id -- get it with:
  #   az ad sp show --id <GRAPH_CLIENT_ID> --query id -o tsv
  New-ServicePrincipal -AppId "<GRAPH_CLIENT_ID>" -ObjectId "<sp-object-id>" -DisplayName "<app-name>"

  New-ManagementScope -Name "ReportSenderMailboxOnly" `
    -RecipientRestrictionFilter "PrimarySmtpAddress -eq '<GRAPH_SENDER_MAILBOX>'"

  New-ManagementRoleAssignment -Role "Application Mail.Send" `
    -App "<GRAPH_CLIENT_ID>" -CustomResourceScope "ReportSenderMailboxOnly"

  # Verify: intended mailbox -> InScope True; a different mailbox -> False.
  Test-ServicePrincipalAuthorization -Identity "<GRAPH_CLIENT_ID>" -Resource "<GRAPH_SENDER_MAILBOX>"

Then set GRAPH_SENDER_MAILBOX and GRAPH_REPORT_RECIPIENT (see .env.example).
"""
import json
import logging
import os

from graph_client import GraphClient

log = logging.getLogger("mailer")

GRAPH_SENDER_MAILBOX = os.environ.get("GRAPH_SENDER_MAILBOX")
GRAPH_REPORT_RECIPIENT = os.environ.get("GRAPH_REPORT_RECIPIENT")


def send_report_email(client: GraphClient, subject: str, html_body: str) -> bool:
    """POST html_body as a sendMail message. Returns False and just logs if
    GRAPH_SENDER_MAILBOX/GRAPH_REPORT_RECIPIENT aren't set (Project 1's
    "not configured -> skip, don't fail the run" behavior)."""
    if not GRAPH_SENDER_MAILBOX or not GRAPH_REPORT_RECIPIENT:
        log.info(json.dumps({"event": "report_email_not_sent", "reason": "graph_mail_not_configured"}))
        return False

    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [{"emailAddress": {"address": GRAPH_REPORT_RECIPIENT}}],
        },
        "saveToSentItems": "false",
    }
    client.post(f"/users/{GRAPH_SENDER_MAILBOX}/sendMail", json=message)
    log.info(json.dumps({"event": "report_email_sent", "recipient": GRAPH_REPORT_RECIPIENT}))
    return True
