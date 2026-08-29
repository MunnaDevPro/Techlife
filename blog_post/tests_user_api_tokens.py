# blog_post/tests_user_api_tokens.py
"""
Tests for the per-user personal API token system.

Covers:
  - Token generation: hash storage, prefix, raw token never persisted
  - Authentication: success, bad token, revoked, expired, inactive user
  - Per-user rate limiting: hourly and daily limits
  - Post creation via personal token: correct author, pending status
  - Required field gate: missing title/description/category_slug rejected
  - Idempotency via original_content_hash
  - Integration: generate token → POST → post appears under user
"""
import hashlib
import secrets
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import UserAPIToken
from blog_post.models import AutomationPublishLog, BlogPost, Category
from django.contrib.auth import get_user_model

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# Helper: minimal valid user-token POST payload
# ─────────────────────────────────────────────────────────────────────────────

def _valid_payload(category_slug, extra=None):
    payload = {
        "title": "Test Post from Personal Token",
        "description": "<p>" + ("A" * 160) + "</p>",  # > 150 chars plain text
        "category_slug": category_slug,
    }
    if extra:
        payload.update(extra)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# Model tests
# ─────────────────────────────────────────────────────────────────────────────

class UserAPITokenModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="tokenuser@example.com",
            password="Password123!",
            first_name="Token",
            last_name="User",
        )

    def test_generate_returns_instance_and_raw_token(self):
        token_obj, raw_token = UserAPIToken.generate(self.user, name="My Site")
        self.assertIsNotNone(token_obj.pk)
        self.assertTrue(raw_token.startswith("techlife_user_"))
        self.assertIsInstance(raw_token, str)
        self.assertGreater(len(raw_token), 20)

    def test_raw_token_not_stored(self):
        token_obj, raw_token = UserAPIToken.generate(self.user)
        # DB record should not contain the raw token anywhere
        self.assertNotEqual(token_obj.hashed_token, raw_token)
        self.assertNotIn(raw_token, token_obj.token_prefix)

    def test_hashed_token_is_sha256(self):
        token_obj, raw_token = UserAPIToken.generate(self.user)
        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        self.assertEqual(token_obj.hashed_token, expected_hash)

    def test_token_prefix_is_first_20_chars(self):
        token_obj, raw_token = UserAPIToken.generate(self.user)
        self.assertEqual(token_obj.token_prefix, raw_token[:20])

    def test_authenticate_returns_token_for_valid_raw(self):
        token_obj, raw_token = UserAPIToken.generate(self.user)
        found = UserAPIToken.authenticate(raw_token)
        self.assertIsNotNone(found)
        self.assertEqual(found.pk, token_obj.pk)

    def test_authenticate_returns_none_for_wrong_token(self):
        UserAPIToken.generate(self.user)
        found = UserAPIToken.authenticate("techlife_user_wrongtoken00000000")
        self.assertIsNone(found)

    def test_revoke_sets_is_active_false(self):
        token_obj, _ = UserAPIToken.generate(self.user)
        self.assertTrue(token_obj.is_active)
        token_obj.revoke()
        token_obj.refresh_from_db()
        self.assertFalse(token_obj.is_active)
        self.assertIsNotNone(token_obj.revoked_at)

    def test_is_expired_false_for_no_expiry(self):
        token_obj, _ = UserAPIToken.generate(self.user)
        self.assertFalse(token_obj.is_expired)

    def test_is_expired_true_for_past_expiry(self):
        token_obj, _ = UserAPIToken.generate(self.user)
        token_obj.expires_at = timezone.now() - timedelta(seconds=1)
        token_obj.save()
        self.assertTrue(token_obj.is_expired)

    def test_multiple_tokens_per_user(self):
        UserAPIToken.generate(self.user, name="Site 1")
        UserAPIToken.generate(self.user, name="Site 2")
        self.assertEqual(UserAPIToken.objects.filter(user=self.user).count(), 2)


# ─────────────────────────────────────────────────────────────────────────────
# Authentication tests (DRF endpoint)
# ─────────────────────────────────────────────────────────────────────────────

class UserAPITokenAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="apiuser@example.com",
            password="Password123!",
            first_name="API",
            last_name="User",
        )
        self.category = Category.objects.create(name="Tech Auth Test", slug="tech-auth-test")
        self.client = APIClient()
        self.url = "/api/blog/posts/"

    def _post_with_token(self, raw_token, payload=None):
        if payload is None:
            payload = _valid_payload(self.category.slug)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        return self.client.post(self.url, payload, format="json")

    def test_valid_token_authenticates(self):
        token_obj, raw_token = UserAPIToken.generate(self.user)
        response = self._post_with_token(raw_token)
        # 201 created (pending) or 422 if content issue — either way, NOT 401/403
        self.assertNotIn(response.status_code, [401, 403])

    def test_invalid_token_returns_401(self):
        response = self._post_with_token("techlife_user_doesnotexist0000000")
        self.assertEqual(response.status_code, 401)

    def test_revoked_token_returns_401(self):
        token_obj, raw_token = UserAPIToken.generate(self.user)
        token_obj.revoke()
        response = self._post_with_token(raw_token)
        self.assertEqual(response.status_code, 401)

    def test_expired_token_returns_401(self):
        token_obj, raw_token = UserAPIToken.generate(self.user)
        token_obj.expires_at = timezone.now() - timedelta(seconds=1)
        token_obj.save()
        response = self._post_with_token(raw_token)
        self.assertEqual(response.status_code, 401)

    def test_inactive_user_token_returns_401(self):
        token_obj, raw_token = UserAPIToken.generate(self.user)
        self.user.is_active = False
        self.user.save()
        response = self._post_with_token(raw_token)
        self.assertEqual(response.status_code, 401)

    def test_missing_bearer_scheme_ignored(self):
        # Automation scheme should not trigger UserAPITokenAuthentication
        self.client.credentials(HTTP_AUTHORIZATION="Automation some_token")
        response = self.client.post(self.url, _valid_payload(self.category.slug), format="json")
        # Should get 401 from Automation auth (wrong token), not 200
        self.assertIn(response.status_code, [401, 403])

    def test_last_used_at_updated_on_auth(self):
        token_obj, raw_token = UserAPIToken.generate(self.user)
        self.assertIsNone(token_obj.last_used_at)
        self._post_with_token(raw_token)
        token_obj.refresh_from_db()
        self.assertIsNotNone(token_obj.last_used_at)


# ─────────────────────────────────────────────────────────────────────────────
# Post creation tests
# ─────────────────────────────────────────────────────────────────────────────

class UserTokenPostCreationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="poster@example.com",
            password="Password123!",
            first_name="Post",
            last_name="User",
        )
        self.category = Category.objects.create(name="User Token Cat", slug="user-token-cat")
        self.client = APIClient()
        self.url = "/api/blog/posts/"
        self.token_obj, self.raw_token = UserAPIToken.generate(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.raw_token}")

    def test_post_created_with_correct_author(self):
        response = self.client.post(
            self.url,
            _valid_payload(self.category.slug),
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        post_id = response.data["post_id"]
        post = BlogPost.objects.get(pk=post_id)
        self.assertEqual(post.author, self.user)

    def test_post_created_with_pending_status(self):
        response = self.client.post(
            self.url,
            _valid_payload(self.category.slug),
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        post = BlogPost.objects.get(pk=response.data["post_id"])
        self.assertEqual(post.status, "pending")

    def test_missing_title_returns_422(self):
        payload = _valid_payload(self.category.slug)
        del payload["title"]
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 422)
        self.assertIn("title", response.data.get("failed_gates", []))

    def test_missing_description_returns_422(self):
        payload = _valid_payload(self.category.slug)
        del payload["description"]
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 422)
        self.assertIn("description", response.data.get("failed_gates", []))

    def test_missing_category_slug_returns_422(self):
        payload = _valid_payload(self.category.slug)
        del payload["category_slug"]
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 422)
        self.assertIn("category_slug", response.data.get("failed_gates", []))

    def test_forbidden_fields_rejected(self):
        payload = _valid_payload(self.category.slug, extra={"author": 1})
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data.get("code"), "FORBIDDEN_FIELDS")

    def test_idempotency_via_content_hash(self):
        hash_val = hashlib.sha256(b"unique_content_for_idempotency_test").hexdigest()
        payload = _valid_payload(self.category.slug, extra={"original_content_hash": hash_val})
        
        r1 = self.client.post(self.url, payload, format="json")
        self.assertEqual(r1.status_code, 201)
        
        r2 = self.client.post(self.url, payload, format="json")
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.data.get("idempotent_replay"))

    def test_audit_log_created_with_user_token_source(self):
        self.client.post(
            self.url,
            _valid_payload(self.category.slug),
            format="json",
        )
        log = AutomationPublishLog.objects.filter(
            token_user=self.user,
            auth_source="user_token",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.token_id, self.token_obj.pk)


# ─────────────────────────────────────────────────────────────────────────────
# Per-user rate limiting tests
# ─────────────────────────────────────────────────────────────────────────────

@override_settings(
    TECHLIFE_USER_TOKEN_HOURLY_REQUEST_LIMIT=3,
    TECHLIFE_USER_TOKEN_DAILY_POST_LIMIT=2,
)
class UserTokenRateLimitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="ratelimit@example.com",
            password="Password123!",
            first_name="Rate",
            last_name="Limited",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="Password123!",
            first_name="Other",
            last_name="User",
        )
        self.category = Category.objects.create(name="RL Cat", slug="rl-cat")
        self.client = APIClient()
        self.url = "/api/blog/posts/"
        _, self.raw_token = UserAPIToken.generate(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.raw_token}")

    def _seed_hourly_logs(self, user, count):
        """Seed audit log entries for hourly check."""
        for _ in range(count):
            AutomationPublishLog.objects.create(
                event_type="published",
                http_status=201,
                auth_source="user_token",
                token_user=user,
                created_at=timezone.now() - timedelta(minutes=30),
            )

    def test_hourly_limit_blocks_at_threshold(self):
        # 3 is the limit; seed 3 logs already
        self._seed_hourly_logs(self.user, 3)
        response = self.client.post(
            self.url,
            _valid_payload(self.category.slug),
            format="json",
        )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data.get("code"), "USER_TOKEN_HOURLY_RATE_LIMIT")

    def test_hourly_limit_is_per_user_not_global(self):
        """Other user's logs should NOT count toward self.user's limit."""
        self._seed_hourly_logs(self.other_user, 3)
        # self.user has 0 requests — should still be allowed
        response = self.client.post(
            self.url,
            _valid_payload(self.category.slug),
            format="json",
        )
        # Should NOT be throttled (might fail for other reasons but not 429-rate-limit)
        if response.status_code == 429:
            self.assertNotEqual(response.data.get("code"), "USER_TOKEN_HOURLY_RATE_LIMIT")

    def test_daily_limit_blocks_after_threshold(self):
        """Seed 2 published logs for today → next request blocked."""
        local_start_approx = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for _ in range(2):
            AutomationPublishLog.objects.create(
                event_type="published",
                http_status=201,
                auth_source="user_token",
                token_user=self.user,
                created_at=local_start_approx + timedelta(hours=1),
            )
        response = self.client.post(
            self.url,
            _valid_payload(self.category.slug),
            format="json",
        )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data.get("code"), "USER_TOKEN_DAILY_LIMIT_REACHED")

    def test_retry_after_header_present_on_rate_limit(self):
        self._seed_hourly_logs(self.user, 3)
        response = self.client.post(
            self.url,
            _valid_payload(self.category.slug),
            format="json",
        )
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)


# ─────────────────────────────────────────────────────────────────────────────
# Integration test: full flow
# ─────────────────────────────────────────────────────────────────────────────

class UserTokenIntegrationTest(TestCase):
    """
    Simulates: user generates token → external POST with that token
    → post appears under user, visible in DB.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="integrationuser@example.com",
            password="Password123!",
            first_name="Integration",
            last_name="Test",
        )
        self.category = Category.objects.create(name="Integration Cat", slug="integration-cat")

    def test_full_flow(self):
        # 1. User generates a token (simulate what the dashboard does)
        token_obj, raw_token = UserAPIToken.generate(self.user, name="My External Blog")
        self.assertTrue(raw_token.startswith("techlife_user_"))
        self.assertTrue(token_obj.is_active)

        # 2. External script POSTs a blog post using the Bearer token
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw_token}")

        unique_hash = hashlib.sha256(b"integration_test_unique_content_abc").hexdigest()
        payload = {
            "title": "Integration Test Article",
            "description": "<p>" + ("B" * 200) + "</p>",
            "category_slug": self.category.slug,
            "tags_list": ["integration", "test"],
            "original_content_hash": unique_hash,
        }
        response = client.post("/api/blog/posts/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "pending")

        # 3. Post exists in DB under the correct author
        post = BlogPost.objects.get(pk=response.data["post_id"])
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.status, "pending")
        self.assertEqual(post.title, "Integration Test Article")

        # 4. Audit log entry created
        log = AutomationPublishLog.objects.filter(
            post=post,
            auth_source="user_token",
            token_user=self.user,
        ).first()
        self.assertIsNotNone(log)

        # 5. Idempotent re-submission returns 200, no duplicate
        response2 = client.post("/api/blog/posts/", payload, format="json")
        self.assertEqual(response2.status_code, 200)
        self.assertTrue(response2.data["idempotent_replay"])
        self.assertEqual(BlogPost.objects.filter(author=self.user).count(), 1)

        # 6. Token revocation blocks further requests
        token_obj.revoke()
        response3 = client.post("/api/blog/posts/", payload, format="json")
        self.assertEqual(response3.status_code, 401)


# ─────────────────────────────────────────────────────────────────────────────
# Token management API endpoint tests
# ─────────────────────────────────────────────────────────────────────────────

class TokenManagementAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="mgmt@example.com",
            password="Password123!",
            first_name="Mgmt",
            last_name="User",
        )
        self.client = APIClient()
        self.client.force_login(self.user)

    def test_list_tokens_empty(self):
        response = self.client.get("/api/account/tokens/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_create_token_returns_raw_once(self):
        response = self.client.post(
            "/api/account/tokens/",
            {"name": "Test Token"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("raw_token", response.data)
        self.assertTrue(response.data["raw_token"].startswith("techlife_user_"))
        # Verify token is in DB
        self.assertEqual(UserAPIToken.objects.filter(user=self.user).count(), 1)

    def test_list_shows_token_without_raw_value(self):
        UserAPIToken.generate(self.user, name="Visible Token")
        response = self.client.get("/api/account/tokens/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        token_data = response.data[0]
        self.assertIn("token_prefix", token_data)
        self.assertNotIn("hashed_token", token_data)
        self.assertNotIn("raw_token", token_data)

    def test_revoke_token(self):
        token_obj, _ = UserAPIToken.generate(self.user, name="To Revoke")
        response = self.client.post(f"/api/account/tokens/{token_obj.pk}/revoke/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "revoked")
        token_obj.refresh_from_db()
        self.assertFalse(token_obj.is_active)

    def test_cannot_revoke_another_users_token(self):
        other_user = User.objects.create_user(
            email="other2@example.com",
            password="Password123!",
        )
        other_token, _ = UserAPIToken.generate(other_user)
        response = self.client.post(f"/api/account/tokens/{other_token.pk}/revoke/")
        self.assertEqual(response.status_code, 404)
        other_token.refresh_from_db()
        self.assertTrue(other_token.is_active)  # unchanged

    def test_unauthenticated_cannot_access(self):
        anon_client = APIClient()
        response = anon_client.get("/api/account/tokens/")
        self.assertEqual(response.status_code, 403)
