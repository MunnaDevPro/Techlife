"""
integrations/meta/tests/test_utils.py
──────────────────────────────────────
Unit tests for integrations.meta.utils

Tests cover:
  • SHA-256 hashing normalisation
  • Phone number hashing
  • Event ID format and uniqueness
  • Cookie extraction from request
  • Client IP resolution (X-Forwarded-For)
  • build_user_data composition and PII masking
"""
import hashlib
import time
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from integrations.meta.utils import (
    build_user_data,
    generate_event_id,
    get_client_ip,
    get_client_user_agent,
    get_fbp,
    get_fbc,
    sha256_hash,
    sha256_hash_phone,
)


class SHA256HashTests(TestCase):
    """Tests for sha256_hash()"""

    def _expected(self, value: str) -> str:
        return hashlib.sha256(value.strip().lower().encode()).hexdigest()

    def test_basic_email(self):
        result = sha256_hash("User@Example.COM")
        self.assertEqual(result, self._expected("user@example.com"))

    def test_whitespace_stripped(self):
        result = sha256_hash("  hello@world.com  ")
        self.assertEqual(result, self._expected("hello@world.com"))

    def test_already_lowercase(self):
        result = sha256_hash("already@lower.com")
        self.assertEqual(result, self._expected("already@lower.com"))

    def test_none_returns_none(self):
        self.assertIsNone(sha256_hash(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(sha256_hash(""))

    def test_whitespace_only_returns_none(self):
        self.assertIsNone(sha256_hash("   "))

    def test_returns_64_char_hex(self):
        result = sha256_hash("test@test.com")
        self.assertEqual(len(result), 64)
        self.assertRegex(result, r"^[0-9a-f]{64}$")


class PhoneHashTests(TestCase):
    """Tests for sha256_hash_phone()"""

    def _hash(self, phone: str) -> str:
        import re
        cleaned = re.sub(r"[^\d+]", "", phone.strip())
        return hashlib.sha256(cleaned.encode()).hexdigest()

    def test_strips_formatting(self):
        result = sha256_hash_phone("+1 (800) 555-1234")
        self.assertEqual(result, self._hash("+18005551234"))

    def test_plain_digits(self):
        result = sha256_hash_phone("01712345678")
        self.assertEqual(result, self._hash("01712345678"))

    def test_none_returns_none(self):
        self.assertIsNone(sha256_hash_phone(None))

    def test_empty_returns_none(self):
        self.assertIsNone(sha256_hash_phone(""))


class GenerateEventIdTests(TestCase):
    """Tests for generate_event_id()"""

    def test_starts_with_evt_prefix(self):
        eid = generate_event_id()
        self.assertTrue(eid.startswith("evt_"), f"Expected 'evt_' prefix, got: {eid}")

    def test_contains_three_parts(self):
        eid = generate_event_id()
        parts = eid.split("_", 2)
        self.assertEqual(len(parts), 3)

    def test_timestamp_part_is_numeric(self):
        eid = generate_event_id()
        _, ts_str, _ = eid.split("_", 2)
        self.assertTrue(ts_str.isdigit(), f"Timestamp not numeric: {ts_str}")

    def test_uuid_part_is_hex(self):
        eid = generate_event_id()
        _, _, uid = eid.split("_", 2)
        self.assertRegex(uid, r"^[0-9a-f]{32}$")

    def test_uniqueness(self):
        ids = {generate_event_id() for _ in range(100)}
        self.assertEqual(len(ids), 100, "Event IDs are not unique")

    def test_timestamp_is_recent(self):
        before = int(time.time() * 1000)
        eid = generate_event_id()
        after = int(time.time() * 1000)
        _, ts_str, _ = eid.split("_", 2)
        ts = int(ts_str)
        self.assertGreaterEqual(ts, before)
        self.assertLessEqual(ts, after)


class RequestHelperTests(TestCase):
    """Tests for get_client_ip, get_client_user_agent, get_fbp, get_fbc"""

    def setUp(self):
        self.factory = RequestFactory()

    def test_get_client_ip_from_remote_addr(self):
        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = "192.168.1.100"
        self.assertEqual(get_client_ip(request), "192.168.1.100")

    def test_get_client_ip_prefers_x_forwarded_for(self):
        request = self.factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.5, 10.0.0.1"
        request.META["REMOTE_ADDR"] = "10.0.0.1"
        self.assertEqual(get_client_ip(request), "203.0.113.5")

    def test_get_client_user_agent(self):
        request = self.factory.get("/", HTTP_USER_AGENT="Mozilla/5.0")
        self.assertEqual(get_client_user_agent(request), "Mozilla/5.0")

    def test_get_fbp_from_cookie(self):
        request = self.factory.get("/")
        request.COOKIES["_fbp"] = "fb.1.12345.abcdef"
        self.assertEqual(get_fbp(request), "fb.1.12345.abcdef")

    def test_get_fbp_missing_returns_none(self):
        request = self.factory.get("/")
        self.assertIsNone(get_fbp(request))

    def test_get_fbc_from_cookie(self):
        request = self.factory.get("/")
        request.COOKIES["_fbc"] = "fb.1.12345.click123"
        self.assertEqual(get_fbc(request), "fb.1.12345.click123")

    def test_get_fbc_constructed_from_fbclid(self):
        request = self.factory.get("/?fbclid=abc123XYZ")
        request.COOKIES = {}
        result = get_fbc(request)
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("fb.1."))
        self.assertIn("abc123XYZ", result)

    def test_get_fbc_missing_returns_none(self):
        request = self.factory.get("/")
        self.assertIsNone(get_fbc(request))


class BuildUserDataTests(TestCase):
    """Tests for build_user_data()"""

    def setUp(self):
        self.factory = RequestFactory()

    def _make_request(self):
        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = "10.0.0.1"
        request.META["HTTP_USER_AGENT"] = "TestBrowser/1.0"
        request.COOKIES = {}
        # Simulate anonymous user
        user = MagicMock()
        user.is_authenticated = False
        request.user = user
        request.meta_pixel_data = {}
        return request

    def test_email_is_hashed(self):
        request = self._make_request()
        data = build_user_data(request, email="Test@User.COM")
        self.assertIn("em", data)
        # Must NOT contain the raw email
        self.assertNotIn("Test@User.COM", str(data.values()))
        # Must be SHA-256 of the normalised value
        expected = sha256_hash("test@user.com")
        self.assertEqual(data["em"], expected)

    def test_phone_is_hashed(self):
        request = self._make_request()
        data = build_user_data(request, phone="+88 01712345678")
        self.assertIn("ph", data)
        self.assertNotIn("+88 01712345678", str(data.values()))

    def test_client_ip_is_plain_text(self):
        request = self._make_request()
        data = build_user_data(request)
        self.assertEqual(data.get("client_ip_address"), "10.0.0.1")

    def test_user_agent_is_plain_text(self):
        request = self._make_request()
        data = build_user_data(request)
        self.assertEqual(data.get("client_user_agent"), "TestBrowser/1.0")

    def test_no_pii_in_plain_text(self):
        """Ensure no raw PII values appear in the output."""
        request = self._make_request()
        data = build_user_data(
            request,
            email="secret@example.com",
            first_name="Alice",
            last_name="Smith",
        )
        values_str = str(list(data.values()))
        self.assertNotIn("secret@example.com", values_str)
        self.assertNotIn("alice", values_str)
        self.assertNotIn("smith", values_str)

    def test_none_values_excluded(self):
        request = self._make_request()
        data = build_user_data(request, email=None, phone=None)
        self.assertNotIn("em", data)
        self.assertNotIn("ph", data)

    def test_authenticated_user_enrichment(self):
        request = self._make_request()
        user = MagicMock()
        user.is_authenticated = True
        user.email = "auth@user.com"
        user.first_name = "Bob"
        user.last_name = "Jones"
        user.pk = 42
        request.user = user

        data = build_user_data(request)
        self.assertIn("em", data)
        self.assertIn("fn", data)
        self.assertIn("ln", data)
        self.assertIn("external_id", data)
