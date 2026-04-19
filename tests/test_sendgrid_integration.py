"""Integration test for SendGrid email delivery.

This test sends a REAL email through SendGrid using the API key
from the .env file. It is marked with pytest.mark.integration so
it can be skipped in CI environments where no API key is available.

Run with:
    pytest tests/test_sendgrid_integration.py -v

Run ONLY integration tests:
    pytest tests/test_sendgrid_integration.py -v -m integration

Skip integration tests:
    pytest tests/ -v -m "not integration"
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.alerts import send_reminder_email, AlertError, _send_email


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_sendgrid_config():
    """Return (api_key, from_email, to_email) or None if not configured."""
    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("ALERT_FROM_EMAIL")
    to_email = os.getenv("ALERT_TO_EMAIL")
    if api_key and from_email and to_email and not api_key.startswith("your_"):
        return api_key, from_email, to_email
    return None


# Skip entire module if SendGrid is not configured
pytestmark = pytest.mark.skipif(
    _get_sendgrid_config() is None,
    reason="SendGrid not configured — set SENDGRID_API_KEY, ALERT_FROM_EMAIL, ALERT_TO_EMAIL in .env",
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestSendGridIntegration:
    """Real SendGrid API integration tests."""

    def test_send_simple_email(self):
        """Send a simple HTML email via SendGrid and verify 200/202 response."""
        config = _get_sendgrid_config()
        assert config is not None, "SendGrid not configured"
        _, _, to_email = config

        # Should not raise — if it does, the test fails with the real error
        _send_email(
            to_email=to_email,
            subject="[Lazarus Integration Test] Simple Email",
            html_body="""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Lazarus Protocol — Integration Test</h2>
                <p>This is a <strong>test email</strong> sent by the Lazarus Protocol
                integration test suite.</p>
                <p>If you received this, SendGrid integration is working correctly.</p>
                <hr>
                <p style="color: #666; font-size: 12px;">
                    This email was sent automatically by pytest. You can safely ignore it.
                </p>
            </div>
            """,
        )

    @pytest.mark.integration
    def test_send_reminder_email(self):
        """Send a reminder email (the actual alert format) via SendGrid."""
        config = _get_sendgrid_config()
        assert config is not None
        _, _, to_email = config

        # send_reminder_email uses the real email template
        send_reminder_email(owner_email=to_email, days_remaining=25)

    @pytest.mark.integration
    def test_sendgrid_missing_key_raises(self):
        """Verify that a missing API key raises AlertError, not a traceback."""
        original = os.environ.pop("SENDGRID_API_KEY", None)
        try:
            with pytest.raises(AlertError, match="SENDGRID_API_KEY"):
                _send_email(
                    to_email="test@example.com",
                    subject="Should fail",
                    html_body="<p>test</p>",
                )
        finally:
            if original:
                os.environ["SENDGRID_API_KEY"] = original

    @pytest.mark.integration
    def test_sendgrid_missing_from_email_raises(self):
        """Verify that a missing ALERT_FROM_EMAIL raises AlertError."""
        original = os.environ.pop("ALERT_FROM_EMAIL", None)
        try:
            with pytest.raises(AlertError, match="ALERT_FROM_EMAIL"):
                _send_email(
                    to_email="test@example.com",
                    subject="Should fail",
                    html_body="<p>test</p>",
                )
        finally:
            if original:
                os.environ["ALERT_FROM_EMAIL"] = original
