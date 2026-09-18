"""Self-check for mailer.py: skips (and logs, doesn't raise) when mailbox
config is missing; sends the right Graph sendMail body when configured.
Run: python -m unittest test_mailer.py -v
"""
import unittest
from unittest.mock import patch

import mailer
from graph_client import GraphClient
from test_graph_client import FakeCredential, FakeResponse, FakeSession


class SendReportEmailTests(unittest.TestCase):
    def test_skips_and_returns_false_when_not_configured(self):
        session = FakeSession([])
        client = GraphClient(credential=FakeCredential(), session=session)

        with patch.object(mailer, "GRAPH_SENDER_MAILBOX", None), \
             patch.object(mailer, "GRAPH_REPORT_RECIPIENT", None):
            sent = mailer.send_report_email(client, "subject", "<p>body</p>")

        self.assertFalse(sent)
        self.assertEqual(session.calls, [])  # no request attempted

    def test_sends_expected_message_shape_when_configured(self):
        accepted = FakeResponse(202, text="")
        session = FakeSession([accepted])
        client = GraphClient(credential=FakeCredential(), session=session)

        with patch.object(mailer, "GRAPH_SENDER_MAILBOX", "reports@x.com"), \
             patch.object(mailer, "GRAPH_REPORT_RECIPIENT", "tyler@x.com"):
            sent = mailer.send_report_email(client, "Posture report", "<p>body</p>")

        self.assertTrue(sent)
        self.assertEqual(session.calls, ["https://graph.microsoft.com/v1.0/users/reports@x.com/sendMail"])
        self.assertEqual(session.posted_json, [{
            "message": {
                "subject": "Posture report",
                "body": {"contentType": "HTML", "content": "<p>body</p>"},
                "toRecipients": [{"emailAddress": {"address": "tyler@x.com"}}],
            },
            "saveToSentItems": "false",
        }])


if __name__ == "__main__":
    unittest.main()
