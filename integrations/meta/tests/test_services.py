"""
integrations/meta/tests/test_services.py
──────────────────────────────────────────
Unit tests for integrations.meta.services.MetaPixelService

Tests cover:
  • Each track_* method builds a correctly structured CAPI payload
  • event_id is returned to the caller
  • Service is a no-op when META_PIXEL_ID is empty
  • Custom data fields are present in payload
  • User data is hashed (not raw PII)
"""
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings

from integrations.meta.services import MetaPixelService


PIXEL_ID = "1779737933474927"


def _make_service(**settings_overrides):
    """Create a fresh MetaPixelService with given settings."""
    defaults = {
        "META_PIXEL_ID": PIXEL_ID,
        "META_ACCESS_TOKEN": "test_token",
        "META_API_VERSION": "v23.0",
        "META_TEST_EVENT_CODE": "",
    }
    defaults.update(settings_overrides)

    from django.test import override_settings as _override
    return _override(**defaults)


class MetaPixelServiceTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _make_request(self, **kwargs):
        request = self.factory.get("/test/")
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        request.META["HTTP_USER_AGENT"] = "TestAgent/1.0"
        request.META["SERVER_NAME"] = "testserver"
        request.META["SERVER_PORT"] = "80"
        request.COOKIES = {}
        mock_user = MagicMock()
        mock_user.is_authenticated = False
        request.user = mock_user
        request.meta_pixel_data = {
            "client_ip_address": "127.0.0.1",
            "client_user_agent": "TestAgent/1.0",
            "fbp": None,
            "fbc": None,
        }
        return request

    def _make_enabled_service(self):
        from django.conf import settings
        # temporarily override settings
        with patch.object(type(settings), 'META_PIXEL_ID', PIXEL_ID, create=True):
            pass
        svc = MetaPixelService.__new__(MetaPixelService)
        svc._enabled = True
        svc._client = MagicMock()
        svc._client.send_event.return_value = {"events_received": 1}
        return svc

    # ── track_page_view ────────────────────────────────────────────────────────

    @override_settings(META_PIXEL_ID=PIXEL_ID, META_ACCESS_TOKEN="tok", META_API_VERSION="v23.0", META_TEST_EVENT_CODE="")
    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_track_page_view_returns_event_id(self, mock_urlopen):
        import json
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"events_received": 1}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        service = MetaPixelService()
        request = self._make_request()
        result = service.track_page_view(request)
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("evt_"))

    # ── Disabled service ───────────────────────────────────────────────────────

    @override_settings(META_PIXEL_ID="", META_ACCESS_TOKEN="", META_API_VERSION="v23.0", META_TEST_EVENT_CODE="")
    def test_disabled_when_no_pixel_id(self):
        service = MetaPixelService()
        self.assertFalse(service._enabled)

    @override_settings(META_PIXEL_ID="", META_ACCESS_TOKEN="", META_API_VERSION="v23.0", META_TEST_EVENT_CODE="")
    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_returns_none_when_disabled(self, mock_urlopen):
        service = MetaPixelService()
        request = self._make_request()
        result = service.track_lead(request, lead_type="Test", country="BD")
        self.assertIsNone(result)
        mock_urlopen.assert_not_called()

    # ── Payload structure ──────────────────────────────────────────────────────

    def test_build_event_has_required_fields(self):
        svc = self._make_enabled_service()
        request = self._make_request()
        event_id, event = svc._build_event(request, "Lead", {"value": 100})
        self.assertIn("event_name", event)
        self.assertIn("event_time", event)
        self.assertIn("event_id", event)
        self.assertIn("action_source", event)
        self.assertIn("event_source_url", event)
        self.assertIn("user_data", event)
        self.assertIn("custom_data", event)
        self.assertEqual(event["event_name"], "Lead")
        self.assertEqual(event["action_source"], "website")
        self.assertTrue(event_id.startswith("evt_"))

    def test_custom_data_none_values_excluded(self):
        svc = self._make_enabled_service()
        request = self._make_request()
        _, event = svc._build_event(request, "Lead", {"value": 100, "intake": None})
        # None values should be stripped from custom_data
        self.assertNotIn("intake", event.get("custom_data", {}))
        self.assertEqual(event["custom_data"]["value"], 100)

    # ── Individual event helpers ───────────────────────────────────────────────

    def test_build_event_search(self):
        svc = self._make_enabled_service()
        request = self._make_request()
        _, event = svc._build_event(
            request, "Search", {"search_string": "Oxford MBA", "country": "UK"}
        )
        self.assertEqual(event["event_name"], "Search")
        self.assertEqual(event["custom_data"]["search_string"], "Oxford MBA")

    def test_build_event_purchase_currency_uppercased(self):
        svc = self._make_enabled_service()
        request = self._make_request()
        _, event = svc._build_event(request, "Purchase", {"currency": "bdt", "value": 5000})
        # MetaPixelService.track_purchase uppercases currency
        # (test at service level by calling directly)
        self.assertEqual(event["custom_data"]["currency"], "bdt")  # raw from _build_event

    @override_settings(META_PIXEL_ID=PIXEL_ID, META_ACCESS_TOKEN="tok", META_API_VERSION="v23.0", META_TEST_EVENT_CODE="")
    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_track_lead_custom_data(self, mock_urlopen):
        import json
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"events_received": 1}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        service = MetaPixelService()
        request = self._make_request()
        event_id = service.track_lead(
            request,
            lead_type="Inquiry Form",
            country="BD",
            preferred_university="BRAC University",
            degree="BSc",
            course="CSE",
            intake="Fall 2025",
            value=0,
            currency="BDT",
        )
        self.assertIsNotNone(event_id)
        # Verify the payload sent to urlopen contains our custom_data
        call_body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        sent_event = call_body["data"][0]
        self.assertEqual(sent_event["event_name"], "Lead")
        self.assertEqual(sent_event["custom_data"]["lead_type"], "Inquiry Form")
        self.assertEqual(sent_event["custom_data"]["currency"], "BDT")

    @override_settings(META_PIXEL_ID=PIXEL_ID, META_ACCESS_TOKEN="tok", META_API_VERSION="v23.0", META_TEST_EVENT_CODE="")
    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_track_purchase_uppercase_currency(self, mock_urlopen):
        import json
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"events_received": 1}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        service = MetaPixelService()
        request = self._make_request()
        service.track_purchase(request, order_id="ORD-001", value=5000, currency="bdt", service_name="Visa Fee")
        call_body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        sent_event = call_body["data"][0]
        self.assertEqual(sent_event["custom_data"]["currency"], "BDT")

    @override_settings(META_PIXEL_ID=PIXEL_ID, META_ACCESS_TOKEN="tok", META_API_VERSION="v23.0", META_TEST_EVENT_CODE="")
    @patch("integrations.meta.client.urllib.request.urlopen")
    def test_email_hashed_in_payload(self, mock_urlopen):
        import json
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"events_received": 1}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        service = MetaPixelService()
        request = self._make_request()
        service.track_lead(request, email="student@test.com")
        call_body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        user_data = call_body["data"][0]["user_data"]
        # Raw email must not appear
        self.assertNotIn("student@test.com", str(user_data))
        # Hashed value must be present
        self.assertIn("em", user_data)
        self.assertEqual(len(user_data["em"]), 64)
