"""
integrations/meta/tests/test_middleware.py
────────────────────────────────────────────
Unit tests for integrations.meta.middleware.MetaPixelMiddleware

Tests cover:
  • meta_pixel_data dict is attached to every request
  • IP, UA, fbp, fbc are correctly extracted
  • Empty dict when META_PIXEL_ID is not configured
  • No-op when pixel disabled
"""
from unittest.mock import MagicMock

from django.test import RequestFactory, TestCase, override_settings

from integrations.meta.middleware import MetaPixelMiddleware

PIXEL_ID = "1779737933474927"


class MetaPixelMiddlewareTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=MagicMock(status_code=200))

    def _make_middleware(self):
        return MetaPixelMiddleware(self.get_response)

    def _make_request(self, **extra):
        request = self.factory.get("/", **extra)
        request.COOKIES = {}
        return request

    # ── Enabled middleware ─────────────────────────────────────────────────────

    @override_settings(META_PIXEL_ID=PIXEL_ID)
    def test_meta_pixel_data_attached(self):
        mw = self._make_middleware()
        request = self._make_request(REMOTE_ADDR="192.168.1.5", HTTP_USER_AGENT="Chrome/100")
        mw.process_request(request)
        self.assertTrue(hasattr(request, "meta_pixel_data"))
        self.assertIsInstance(request.meta_pixel_data, dict)

    @override_settings(META_PIXEL_ID=PIXEL_ID)
    def test_client_ip_captured(self):
        mw = self._make_middleware()
        request = self._make_request(REMOTE_ADDR="10.0.0.55")
        mw.process_request(request)
        self.assertEqual(request.meta_pixel_data["client_ip_address"], "10.0.0.55")

    @override_settings(META_PIXEL_ID=PIXEL_ID)
    def test_x_forwarded_for_preferred(self):
        mw = self._make_middleware()
        request = self._make_request(
            REMOTE_ADDR="10.0.0.1",
            HTTP_X_FORWARDED_FOR="203.0.113.99, 10.0.0.1",
        )
        mw.process_request(request)
        self.assertEqual(request.meta_pixel_data["client_ip_address"], "203.0.113.99")

    @override_settings(META_PIXEL_ID=PIXEL_ID)
    def test_user_agent_captured(self):
        mw = self._make_middleware()
        request = self._make_request(HTTP_USER_AGENT="Mozilla/5.0 TestBrowser")
        mw.process_request(request)
        self.assertEqual(request.meta_pixel_data["client_user_agent"], "Mozilla/5.0 TestBrowser")

    @override_settings(META_PIXEL_ID=PIXEL_ID)
    def test_fbp_cookie_captured(self):
        mw = self._make_middleware()
        request = self._make_request()
        request.COOKIES["_fbp"] = "fb.1.123456.abcdef"
        mw.process_request(request)
        self.assertEqual(request.meta_pixel_data["fbp"], "fb.1.123456.abcdef")

    @override_settings(META_PIXEL_ID=PIXEL_ID)
    def test_fbc_cookie_captured(self):
        mw = self._make_middleware()
        request = self._make_request()
        request.COOKIES["_fbc"] = "fb.1.123456.clickid"
        mw.process_request(request)
        self.assertEqual(request.meta_pixel_data["fbc"], "fb.1.123456.clickid")

    @override_settings(META_PIXEL_ID=PIXEL_ID)
    def test_missing_cookies_are_none(self):
        mw = self._make_middleware()
        request = self._make_request()
        mw.process_request(request)
        self.assertIsNone(request.meta_pixel_data["fbp"])
        self.assertIsNone(request.meta_pixel_data["fbc"])

    # ── Disabled middleware ────────────────────────────────────────────────────

    @override_settings(META_PIXEL_ID="")
    def test_empty_dict_when_disabled(self):
        mw = self._make_middleware()
        request = self._make_request(REMOTE_ADDR="10.0.0.1", HTTP_USER_AGENT="Browser/1")
        mw.process_request(request)
        self.assertTrue(hasattr(request, "meta_pixel_data"))
        self.assertEqual(request.meta_pixel_data, {})

    @override_settings(META_PIXEL_ID="")
    def test_disabled_middleware_does_not_read_cookies(self):
        """When disabled, middleware must not touch cookies at all."""
        mw = self._make_middleware()
        request = self._make_request()
        # Simulate cookie access tracking
        request.COOKIES = MagicMock()
        request.COOKIES.get.return_value = None
        mw.process_request(request)
        request.COOKIES.get.assert_not_called()

    # ── Keys always present when enabled ──────────────────────────────────────

    @override_settings(META_PIXEL_ID=PIXEL_ID)
    def test_all_expected_keys_present(self):
        mw = self._make_middleware()
        request = self._make_request()
        mw.process_request(request)
        for key in ("client_ip_address", "client_user_agent", "fbp", "fbc"):
            self.assertIn(key, request.meta_pixel_data, f"Missing key: {key}")
