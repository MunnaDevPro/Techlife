"""
integrations/meta/tests/test_client.py
────────────────────────────────────────
Unit tests for integrations.meta.client.MetaAPIClient

Tests cover:
  • Successful HTTP POST and JSON parsing
  • Retry logic on transient network errors
  • 4xx errors are NOT retried
  • Timeout handling (no crash)
  • Access token is never logged
  • No-op when META_PIXEL_ID is missing
"""
import json
import logging
from io import BytesIO
from unittest.mock import MagicMock, call, patch

from django.test import TestCase, override_settings

from integrations.meta.client import MetaAPIClient, _MAX_RETRIES


PIXEL_ID = "1779737933474927"
ACCESS_TOKEN = "test_access_token_secret"
API_VERSION = "v23.0"


@override_settings(
    META_PIXEL_ID=PIXEL_ID,
    META_ACCESS_TOKEN=ACCESS_TOKEN,
    META_API_VERSION=API_VERSION,
    META_TEST_EVENT_CODE="",
)
class MetaAPIClientTests(TestCase):

    def _make_client(self):
        return MetaAPIClient()

    def _sample_event(self):
        return {
            "event_name": "Lead",
            "event_time": 1722178345,
            "event_id": "evt_1722178345000_abc123",
            "action_source": "website",
            "user_data": {"client_ip_address": "127.0.0.1"},
        }

    def _mock_response(self, body: dict):
        """Return a mock urllib response."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(body).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    # ── Successful send ────────────────────────────────────────────────────────

    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_successful_send_returns_response(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response({"events_received": 1})
        client = self._make_client()
        result = client.send_event(self._sample_event())
        self.assertEqual(result, {"events_received": 1})

    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_send_posts_to_correct_url(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response({})
        client = self._make_client()
        client.send_event(self._sample_event())
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        self.assertIn(PIXEL_ID, req.full_url)
        self.assertIn("events", req.full_url)
        self.assertIn(API_VERSION, req.full_url)

    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_access_token_in_payload_not_url(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response({})
        client = self._make_client()
        client.send_event(self._sample_event())
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        # Token must NOT be in the URL
        self.assertNotIn(ACCESS_TOKEN, req.full_url)
        # Token MUST be in the POST body
        body = json.loads(req.data.decode())
        self.assertEqual(body["access_token"], ACCESS_TOKEN)

    # ── Test event code ───────────────────────────────────────────────────────

    @override_settings(META_TEST_EVENT_CODE="TEST12345")
    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_test_event_code_included_in_payload(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response({})
        client = self._make_client()
        client.send_event(self._sample_event())
        body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        self.assertEqual(body["test_event_code"], "TEST12345")

    # ── Retry logic ───────────────────────────────────────────────────────────

    @patch("integrations.meta.client.time.sleep")
    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_retries_on_network_error(self, mock_urlopen, mock_sleep):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        client = self._make_client()
        result = client.send_event(self._sample_event())
        self.assertIsNone(result)
        self.assertEqual(mock_urlopen.call_count, _MAX_RETRIES)

    @patch("integrations.meta.client.time.sleep")
    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_no_retry_on_4xx_error(self, mock_urlopen, mock_sleep):
        import urllib.error
        http_error = urllib.error.HTTPError(
            url="https://graph.facebook.com/",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=BytesIO(b'{"error": "bad request"}'),
        )
        mock_urlopen.side_effect = http_error
        client = self._make_client()
        result = client.send_event(self._sample_event())
        self.assertIsNone(result)
        # Should only be called ONCE (no retry on 4xx)
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("integrations.meta.client.time.sleep")
    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_succeeds_after_transient_failure(self, mock_urlopen, mock_sleep):
        import urllib.error
        mock_urlopen.side_effect = [
            urllib.error.URLError("timeout"),
            self._mock_response({"events_received": 1}),
        ]
        client = self._make_client()
        result = client.send_event(self._sample_event())
        self.assertEqual(result, {"events_received": 1})
        self.assertEqual(mock_urlopen.call_count, 2)

    # ── Disabled state ────────────────────────────────────────────────────────

    @override_settings(META_PIXEL_ID="", META_ACCESS_TOKEN="")
    def test_disabled_when_no_pixel_id(self):
        client = MetaAPIClient()
        self.assertFalse(client._enabled)

    @override_settings(META_PIXEL_ID="", META_ACCESS_TOKEN="")
    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_no_http_call_when_disabled(self, mock_urlopen):
        client = MetaAPIClient()
        result = client.send_event(self._sample_event())
        self.assertIsNone(result)
        mock_urlopen.assert_not_called()

    # ── Logging (token safety) ────────────────────────────────────────────────

    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_access_token_not_in_success_log(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response({"events_received": 1})
        client = self._make_client()
        with self.assertLogs("integrations.meta", level="INFO") as cm:
            client.send_event(self._sample_event())
        log_output = " ".join(cm.output)
        self.assertNotIn(ACCESS_TOKEN, log_output)

    @patch("integrations.meta.client.time.sleep")
    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_access_token_not_in_failure_log(self, mock_urlopen, mock_sleep):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("err")
        client = self._make_client()
        with self.assertLogs("integrations.meta", level="WARNING") as cm:
            client.send_event(self._sample_event())
        log_output = " ".join(cm.output)
        self.assertNotIn(ACCESS_TOKEN, log_output)
