import hashlib
from django.test import TestCase, override_settings
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse

from blog_post.models import BlogPost, Category, SubCategory
from tags.models import Tag
from blog_post.forms import BlogPostForm
from blog_post.serializers import BlogPostListSerializer, BlogPostDetailSerializer
from dashboard.services.content_service import approve_post

User = get_user_model()


class BlogPostStatusLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="author@example.com",
            password="Password123!",
            first_name="Author",
            last_name="User"
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPassword123!",
            first_name="Admin",
            last_name="User"
        )
        self.category = Category.objects.create(name="Tech", slug="tech")
        self.client = APIClient()

    def test_new_post_defaults_to_pending(self):
        post = BlogPost.objects.create(
            title="First Post",
            description="Content for first post",
            author=self.user,
            category=self.category
        )
        self.assertEqual(post.status, "pending")

    def test_model_does_not_auto_publish(self):
        post = BlogPost.objects.create(
            title="Unique Non-Duplicate Post",
            description="Brand new unique description",
            author=self.user,
            category=self.category
        )
        self.assertNotEqual(post.status, "published")
        self.assertEqual(post.status, "pending")

    def test_explicitly_supplied_status_preserved(self):
        post = BlogPost.objects.create(
            title="Explicitly Published Post",
            description="Explicitly published content",
            author=self.user,
            category=self.category,
            status="published"
        )
        self.assertEqual(post.status, "published")

        post_rejected = BlogPost.objects.create(
            title="Explicitly Rejected Post",
            description="Explicitly rejected content",
            author=self.user,
            category=self.category,
            status="rejected"
        )
        self.assertEqual(post_rejected.status, "rejected")

    def test_editing_published_post_remains_published(self):
        post = BlogPost.objects.create(
            title="Published Post to Edit",
            description="Original description",
            author=self.user,
            category=self.category,
            status="published"
        )
        self.assertEqual(post.status, "published")

        post.description = "Updated description for published post"
        post.save()
        post.refresh_from_db()
        self.assertEqual(post.status, "published")

    def test_duplicate_content_raises_validation_error_on_clean(self):
        BlogPost.objects.create(
            title="Original Post",
            description="Duplicate content test body",
            author=self.user,
            category=self.category
        )
        duplicate_post = BlogPost(
            title="Original Post",
            description="Duplicate content test body",
            author=self.user,
            category=self.category
        )
        with self.assertRaises(ValidationError):
            duplicate_post.clean()

    def test_duplicate_content_form_validation(self):
        BlogPost.objects.create(
            title="Existing Post Title",
            description="Existing post body content",
            author=self.user,
            category=self.category
        )
        form_data = {
            "title": "Existing Post Title",
            "description": "Existing post body content",
            "category": self.category.id,
        }
        form = BlogPostForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("duplicate content", str(form.errors))

    def test_api_creates_post_as_pending(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "title": "API Created Post",
            "description": "API created post body content",
            "category": self.category.id
        }
        response = self.client.post("/api/blog/posts/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "pending")

        created_post = BlogPost.objects.get(id=response.data["id"])
        self.assertEqual(created_post.status, "pending")

    def test_api_rejects_duplicate_post(self):
        BlogPost.objects.create(
            title="API Existing Post Title",
            description="API existing post body content",
            author=self.user,
            category=self.category
        )
        self.client.force_authenticate(user=self.user)
        payload = {
            "title": "API Existing Post Title",
            "description": "API existing post body content",
            "category": self.category.id
        }
        response = self.client.post("/api/blog/posts/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_publishing(self):
        post = BlogPost.objects.create(
            title="Pending Post for Admin Approval",
            description="Post awaiting admin approval",
            author=self.user,
            category=self.category
        )
        self.assertEqual(post.status, "pending")

        approved_post = approve_post(post.id, self.admin_user)
        self.assertEqual(approved_post.status, "published")


class BlogPostAutomationMetadataTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="writer@example.com",
            password="Password123!",
            first_name="Writer",
            last_name="User"
        )
        self.admin_user = User.objects.create_superuser(
            email="admin_meta@example.com",
            password="AdminPassword123!",
            first_name="Admin",
            last_name="Meta"
        )
        self.category = Category.objects.create(name="AI Tech", slug="ai-tech")
        self.client = APIClient()

    def test_legacy_post_defaults(self):
        post = BlogPost.objects.create(
            title="Legacy Post",
            description="Legacy post description",
            author=self.user,
            category=self.category
        )
        self.assertFalse(post.generated_by_ai)
        self.assertEqual(post.review_decision, "not_reviewed")
        self.assertEqual(post.image_processing_status, "not_started")
        self.assertIsNone(post.source_name)
        self.assertIsNone(post.automation_id)

    def test_source_url_normalization(self):
        post = BlogPost.objects.create(
            title="Source URL Test",
            description="Testing URL normalization",
            author=self.user,
            category=self.category,
            source_url="   EXAMPLE.COM/news/article-123   "
        )
        self.assertEqual(post.source_url, "http://example.com/news/article-123")

    def test_score_bounds_validation(self):
        post_invalid = BlogPost(
            title="Invalid Score Post",
            description="Post with invalid score",
            author=self.user,
            category=self.category,
            quality_score=150
        )
        with self.assertRaises(ValidationError):
            post_invalid.clean()

        post_negative = BlogPost(
            title="Negative Score Post",
            description="Post with negative score",
            author=self.user,
            category=self.category,
            seo_score=-5
        )
        with self.assertRaises(ValidationError):
            post_negative.clean()

    def test_review_decision_choices_validation(self):
        post_invalid_decision = BlogPost(
            title="Invalid Decision Post",
            description="Post with invalid decision",
            author=self.user,
            category=self.category,
            review_decision="super_approved"
        )
        with self.assertRaises(ValidationError):
            post_invalid_decision.clean()

    def test_automation_id_uniqueness_validation(self):
        BlogPost.objects.create(
            title="Pipeline Post 1",
            description="First pipeline run content",
            author=self.user,
            category=self.category,
            automation_id="job_exec_999"
        )
        dup_post = BlogPost(
            title="Pipeline Post 2",
            description="Second pipeline run content",
            author=self.user,
            category=self.category,
            automation_id="job_exec_999"
        )
        with self.assertRaises(ValidationError):
            dup_post.clean()

    def test_public_api_does_not_expose_ai_metadata(self):
        post = BlogPost.objects.create(
            title="AI Post for Public API",
            description="AI generated content for public feed",
            author=self.user,
            category=self.category,
            status="published",
            generated_by_ai=True,
            ai_model="gpt-4o",
            reviewer_model="claude-3-5-sonnet",
            quality_score=95,
            automation_id="auto_12345",
            source_name="Tech Crunch"
        )
        list_serializer = BlogPostListSerializer(instance=post)
        detail_serializer = BlogPostDetailSerializer(instance=post)

        forbidden_keys = [
            'generated_by_ai', 'ai_model', 'reviewer_model',
            'quality_score', 'factual_accuracy_score', 'language_score',
            'seo_score', 'automation_id', 'review_decision', 'source_name'
        ]
        for key in forbidden_keys:
            self.assertNotIn(key, list_serializer.data)
            self.assertNotIn(key, detail_serializer.data)

        # Anonymous public HTTP request
        response = self.client.get(f"/api/blog/posts/{post.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in forbidden_keys:
            self.assertNotIn(key, response.data)

    def test_authenticated_dashboard_post_detail_renders_cotton_metadata_card(self):
        post = BlogPost.objects.create(
            title="Dashboard Detail Post",
            description="Dashboard detail view post content",
            author=self.user,
            category=self.category,
            status="published",
            generated_by_ai=True,
            ai_model="gemini-1.5-pro",
            automation_id="auto_exec_777",
            quality_score=88
        )
        self.client.force_login(self.admin_user)
        url = reverse("dashboard:post_detail", kwargs={"pk": post.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Source &amp; Automation Metadata", html=True)
        self.assertContains(response, "AI Generated")
        self.assertContains(response, "gemini-1.5-pro")


@override_settings(
    TECHLIFE_AUTOMATION_TOKEN="secret-test-token-12345",
    TECHLIFE_AUTOMATION_AUTHOR_USERNAME="techlife_desk"
)
class BlogPostAutomationAuthenticationTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Automation Category", slug="automation-cat")
        self.client = APIClient()
        self.automation_user = User.objects.create_user(
            email="techlife_desk@techlifebd.com",
            password="Password123!",
            first_name="TechLife",
            last_name="Desk",
            is_active=True,
            is_staff=False,
            is_superuser=False
        )

    def test_valid_automation_auth_creates_post_owned_by_automation_user(self):
        headers = {"HTTP_AUTHORIZATION": "Automation secret-test-token-12345"}
        payload = {
            "title": "n8n Automated Post Title",
            "description": "<h2>Comprehensive AI Article</h2><p>This is a long valid article description containing more than 150 characters to pass length validation. It provides clear insights and detailed analysis on modern technology trends, software development, and digital transformation in 2026.</p>",
            "category_slug": self.category.slug,
            "tags_list": ["Tag One", "Tag Two", "Tag Three"],
            "source_name": "TechCrunch",
            "source_url": "https://techcrunch.com/2026/08/18/ai-breakthrough",
            "original_content_hash": "a" * 64,
            "automation_id": "n8n_exec_9999",
            "generated_by_ai": True,
            "ai_model": "gpt-4o",
            "reviewer_model": "claude-3-5-sonnet",
            "review_decision": "approved",
            "quality_score": 94,
            "factual_accuracy_score": 98,
            "language_score": 93,
            "seo_score": 86
        }
        response = self.client.post("/api/blog/posts/", payload, **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "published")

        created_post = BlogPost.objects.get(id=response.data["post_id"])
        self.assertEqual(created_post.author, self.automation_user)
        self.assertEqual(created_post.status, "published")

    def test_invalid_automation_token_returns_401(self):
        headers = {"HTTP_AUTHORIZATION": "Automation wrong-invalid-token"}
        payload = {
            "title": "Post with Invalid Token",
            "description": "Post description content",
            "category": self.category.id
        }
        response = self.client.post("/api/blog/posts/", payload, **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_malformed_automation_header_returns_401(self):
        headers = {"HTTP_AUTHORIZATION": "Automation"}
        payload = {
            "title": "Post with Malformed Header",
            "description": "Post description content",
            "category": self.category.id
        }
        response = self.client.post("/api/blog/posts/", payload, **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(TECHLIFE_AUTOMATION_TOKEN="")
    def test_missing_automation_config_returns_401(self):
        headers = {"HTTP_AUTHORIZATION": "Automation secret-test-token-12345"}
        payload = {
            "title": "Post with Unconfigured Token",
            "description": "Post description content",
            "category": self.category.id
        }
        response = self.client.post("/api/blog/posts/", payload, **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(TECHLIFE_AUTOMATION_AUTHOR_USERNAME="non_existent_author")
    def test_missing_automation_user_returns_401(self):
        headers = {"HTTP_AUTHORIZATION": "Automation secret-test-token-12345"}
        payload = {
            "title": "Post with Missing Author",
            "description": "Post description content",
            "category": self.category.id
        }
        response = self.client.post("/api/blog/posts/", payload, **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_user_returns_401(self):
        self.automation_user.is_active = False
        self.automation_user.save()

        headers = {"HTTP_AUTHORIZATION": "Automation secret-test-token-12345"}
        payload = {
            "title": "Post with Inactive Author",
            "description": "Post description content",
            "category": self.category.id
        }
        response = self.client.post("/api/blog/posts/", payload, **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_or_superuser_user_returns_401(self):
        self.automation_user.is_staff = True
        self.automation_user.save()

        headers = {"HTTP_AUTHORIZATION": "Automation secret-test-token-12345"}
        payload = {
            "title": "Post with Staff Author",
            "description": "Post description content",
            "category": self.category.id
        }
        response = self.client.post("/api/blog/posts/", payload, **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_author_payload_override_prevented(self):
        other_user = User.objects.create_user(
            email="hacker@example.com",
            password="Password123!"
        )
        headers = {"HTTP_AUTHORIZATION": "Automation secret-test-token-12345"}
        payload = {
            "title": "Attempted Author Override Post",
            "description": "Post description content with attempted author override",
            "category": self.category.id,
            "author": other_user.id,
            "author_id": other_user.id,
            "username": "hacker@example.com"
        }
        response = self.client.post("/api/blog/posts/", payload, **headers)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["code"], "AUTOMATION_FORBIDDEN_FIELDS")

    def test_jwt_and_session_authentication_unaffected(self):
        normal_user = User.objects.create_user(
            email="normal_writer@example.com",
            password="Password123!"
        )
        self.client.force_authenticate(user=normal_user)
        payload = {
            "title": "Normal Authenticated User Post",
            "description": "Post content from normal authenticated user",
            "category": self.category.id
        }
        response = self.client.post("/api/blog/posts/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_post = BlogPost.objects.get(id=response.data["id"])
        self.assertEqual(created_post.author, normal_user)

    def test_ensure_automation_author_command(self):
        User.objects.filter(email="techlife_desk@techlifebd.com").delete()
        call_command("ensure_automation_author")

        user = User.objects.get(email="techlife_desk@techlifebd.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.has_usable_password())

        # Test idempotency (run again without error)
        call_command("ensure_automation_author")

        # Test check mode passes when valid
        call_command("ensure_automation_author", check_mode=True)


@override_settings(
    TECHLIFE_AUTOMATION_TOKEN="secret-approval-token-999",
    TECHLIFE_AUTOMATION_AUTHOR_USERNAME="techlife_desk"
)
class BlogPostAutomationApprovalPublishingTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="AI News", slug="ai-news")
        self.client = APIClient()
        self.automation_user = User.objects.create_user(
            email="techlife_desk@techlifebd.com",
            password="Password123!",
            first_name="TechLife",
            last_name="Desk",
            is_active=True,
            is_staff=False,
            is_superuser=False
        )
        self.headers = {"HTTP_AUTHORIZATION": "Automation secret-approval-token-999"}
        self.valid_hash = "a" * 64
        self.valid_payload = {
            "title": "Approved AI Published Post",
            "description": "<h2>Comprehensive AI Article</h2><p>This is a long valid article description containing more than 150 characters to pass length validation. It provides clear insights and detailed analysis on modern technology trends, software development, and digital transformation in 2026.</p>",
            "category_slug": self.category.slug,
            "tags_list": ["Tag Alpha", "Tag Beta", "Tag Gamma"],
            "source_name": "TechCrunch",
            "source_url": "https://techcrunch.com/2026/08/18/ai-breakthrough",
            "original_content_hash": self.valid_hash,
            "automation_id": "n8n_exec_1001",
            "generated_by_ai": True,
            "ai_model": "gpt-4o",
            "reviewer_model": "claude-3-5-sonnet",
            "review_decision": "approved",
            "quality_score": 94,
            "factual_accuracy_score": 98,
            "language_score": 93,
            "seo_score": 86,
            "review_notes": "All facts verified."
        }

    def test_successful_auto_publishing_on_passing_all_gates(self):
        response = self.client.post("/api/blog/posts/", self.valid_payload, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "published")
        self.assertFalse(response.data["idempotent_replay"])
        self.assertTrue(response.data["post_id"])

        created_post = BlogPost.objects.get(id=response.data["post_id"])
        self.assertEqual(created_post.status, "published")
        self.assertEqual(created_post.author, self.automation_user)
        self.assertTrue(created_post.generated_by_ai)

    def test_failed_factual_score_gate_returns_422(self):
        payload = self.valid_payload.copy()
        payload["factual_accuracy_score"] = 80
        response = self.client.post("/api/blog/posts/", payload, **self.headers)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["status"], "rejected")
        self.assertEqual(response.data["code"], "AUTOMATION_APPROVAL_FAILED")
        self.assertIn("factual_accuracy_score", response.data["failed_gates"])
        self.assertEqual(BlogPost.objects.count(), 0)

    def test_failed_review_decision_gate_returns_422(self):
        payload = self.valid_payload.copy()
        payload["review_decision"] = "rejected"
        response = self.client.post("/api/blog/posts/", payload, **self.headers)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("review_decision", response.data["failed_gates"])

    def test_missing_reviewer_model_returns_422(self):
        payload = self.valid_payload.copy()
        payload.pop("reviewer_model")
        response = self.client.post("/api/blog/posts/", payload, **self.headers)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("reviewer_model", response.data["failed_gates"])

    def test_invalid_hash_format_returns_422(self):
        payload = self.valid_payload.copy()
        payload["original_content_hash"] = "short_hash_123"
        response = self.client.post("/api/blog/posts/", payload, **self.headers)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("original_content_hash", response.data["failed_gates"])

    def test_forbidden_payload_fields_returns_422(self):
        payload = self.valid_payload.copy()
        payload["status"] = "published"
        response = self.client.post("/api/blog/posts/", payload, **self.headers)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["code"], "AUTOMATION_FORBIDDEN_FIELDS")

    def test_idempotent_replay_returns_200(self):
        resp1 = self.client.post("/api/blog/posts/", self.valid_payload, **self.headers)
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        post_id = resp1.data["post_id"]

        # Retry exact same request
        resp2 = self.client.post("/api/blog/posts/", self.valid_payload, **self.headers)
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.data["status"], "published")
        self.assertTrue(resp2.data["idempotent_replay"])
        self.assertEqual(resp2.data["post_id"], post_id)
        self.assertEqual(BlogPost.objects.count(), 1)

    def test_idempotency_conflict_returns_409(self):
        p1_payload = self.valid_payload.copy()
        p1_payload["automation_id"] = "auto_A"
        p1_payload["source_url"] = "https://example.com/art-A"
        p1_payload["original_content_hash"] = "b" * 64
        self.client.post("/api/blog/posts/", p1_payload, **self.headers)

        p2_payload = self.valid_payload.copy()
        p2_payload["automation_id"] = "auto_B"
        p2_payload["source_url"] = "https://example.com/art-B"
        p2_payload["original_content_hash"] = "c" * 64
        self.client.post("/api/blog/posts/", p2_payload, **self.headers)

        # Conflict payload combining auto_A and url_B
        conflict_payload = self.valid_payload.copy()
        conflict_payload["automation_id"] = "auto_A"
        conflict_payload["source_url"] = "https://example.com/art-B"
        conflict_payload["original_content_hash"] = "d" * 64

        response = self.client.post("/api/blog/posts/", conflict_payload, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "AUTOMATION_IDEMPOTENCY_CONFLICT")


from unittest.mock import patch, MagicMock
from io import BytesIO
from PIL import Image


@override_settings(
    TECHLIFE_AUTOMATION_TOKEN="secret-img-token-777",
    TECHLIFE_AUTOMATION_AUTHOR_USERNAME="techlife_desk"
)
class BlogPostAutomationImageLocalizationTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Tech", slug="tech")
        self.client = APIClient()
        self.automation_user = User.objects.create_user(
            email="techlife_desk@techlifebd.com",
            password="Password123!",
            first_name="TechLife",
            last_name="Desk",
            is_active=True,
            is_staff=False,
            is_superuser=False
        )
        self.headers = {"HTTP_AUTHORIZATION": "Automation secret-img-token-777"}
        self.valid_hash = "f" * 64

        # Generate mock 2000x1500 JPEG image bytes
        bio = BytesIO()
        img = Image.new("RGB", (2000, 1500), color="blue")
        img.save(bio, format="JPEG")
        self.sample_jpeg_bytes = bio.getvalue()

        self.payload = {
            "title": "Local Image Published Post",
            "description": "<h2>Comprehensive AI Article</h2><p>This is a long valid article description containing more than 150 characters to pass length validation. It provides clear insights and detailed analysis on modern technology trends, software development, and digital transformation in 2026.</p>",
            "category_slug": self.category.slug,
            "tags_list": ["Tag Red", "Tag Green", "Tag Blue"],
            "source_name": "Reuters",
            "source_url": "https://reuters.com/article/tech-2026",
            "source_image_url": "https://reuters.com/images/hero.jpg",
            "original_content_hash": self.valid_hash,
            "automation_id": "n8n_img_exec_1",
            "generated_by_ai": True,
            "ai_model": "gpt-4o",
            "reviewer_model": "claude-3-5-sonnet",
            "review_decision": "approved",
            "quality_score": 95,
            "factual_accuracy_score": 99,
            "language_score": 94,
            "seo_score": 88
        }

    @patch("socket.getaddrinfo")
    @patch("requests.Session.get")
    def test_valid_image_download_resizing_webp_conversion(self, mock_get, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 80))
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "image/jpeg"}
        mock_resp.iter_content.return_value = [self.sample_jpeg_bytes]
        mock_get.return_value = mock_resp

        response = self.client.post("/api/blog/posts/", self.payload, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        post = BlogPost.objects.get(id=response.data["post_id"])
        self.assertEqual(post.image_processing_status, "processed")
        self.assertTrue(post.featured_image.name.endswith(".webp"))
        self.assertEqual(post.source_image_url, "https://reuters.com/images/hero.jpg")

    @patch("socket.getaddrinfo")
    def test_blocked_ip_range_returns_422_ssrf(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("127.0.0.1", 80))
        ]
        response = self.client.post("/api/blog/posts/", self.payload, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["code"], "SOURCE_IMAGE_PROCESSING_FAILED")
        self.assertEqual(response.data["image_error"], "BLOCKED_IMAGE_HOST")

    @patch("socket.getaddrinfo")
    def test_cloud_metadata_ip_blocked_ssrf(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("169.254.169.254", 80))
        ]
        response = self.client.post("/api/blog/posts/", self.payload, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["image_error"], "BLOCKED_IMAGE_HOST")

    @patch("socket.getaddrinfo")
    @patch("requests.Session.get")
    def test_redirect_to_blocked_ip_returns_422(self, mock_get, mock_getaddrinfo):
        mock_getaddrinfo.side_effect = [
            [(2, 1, 6, "", ("93.184.216.34", 80))], # first hop
            [(2, 1, 6, "", ("10.0.0.1", 80))]        # redirect hop
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 302
        mock_resp.headers = {"Location": "http://10.0.0.1/private-img.jpg"}
        mock_get.return_value = mock_resp

        response = self.client.post("/api/blog/posts/", self.payload, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["image_error"], "IMAGE_REDIRECT_BLOCKED")

    @patch("socket.getaddrinfo")
    @patch("requests.Session.get")
    def test_oversized_image_returns_422(self, mock_get, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 80))
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "image/jpeg"}
        # Yield 10MB chunk (exceeding 8MB default)
        mock_resp.iter_content.return_value = [b"X" * (9 * 1024 * 1024)]
        mock_get.return_value = mock_resp

        response = self.client.post("/api/blog/posts/", self.payload, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["image_error"], "IMAGE_TOO_LARGE")

    @patch("socket.getaddrinfo")
    @patch("requests.Session.get")
    def test_corrupt_image_bytes_returns_422(self, mock_get, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 80))
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "image/jpeg"}
        mock_resp.iter_content.return_value = [b"NOT_A_VALID_IMAGE_DATA"]
        mock_get.return_value = mock_resp

        response = self.client.post("/api/blog/posts/", self.payload, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["image_error"], "INVALID_IMAGE_CONTENT")


@override_settings(
    TECHLIFE_AUTOMATION_TOKEN="secret-sanitizer-token-888",
    TECHLIFE_AUTOMATION_AUTHOR_USERNAME="techlife_desk"
)
class BlogPostAutomationContentSanitizationTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Tech", slug="tech")
        self.client = APIClient()
        self.automation_user = User.objects.create_user(
            email="techlife_desk@techlifebd.com",
            password="Password123!",
            first_name="TechLife",
            last_name="Desk",
            is_active=True,
            is_staff=False,
            is_superuser=False
        )
        self.headers = {"HTTP_AUTHORIZATION": "Automation secret-sanitizer-token-888"}
        self.valid_hash = "e" * 64

        self.long_valid_text = (
            "<h2>Artificial Intelligence Advancement in 2026</h2>"
            "<p>Artificial intelligence systems are rapidly progressing across industry sectors. "
            "Engineers and researchers have achieved unprecedented benchmarks in reasoning, software synthesis, "
            "and multi-modal processing efficiency.</p>"
            "<p>Key milestones include:</p>"
            "<ul>"
            "<li><strong>Enhanced Efficiency:</strong> Reduced energy consumption during training.</li>"
            "<li><strong>Improved Accuracy:</strong> Fact-checking mechanisms integrated at generation.</li>"
            "</ul>"
            "<p>For more details, visit <a href=\"https://example.com/ai-report\">Official AI Benchmark Report</a>.</p>"
        )

        self.payload = {
            "title": "Clean AI Article Title",
            "subtitle": "Overview of progress",
            "description": self.long_valid_text,
            "category_slug": self.category.slug,
            "tags_list": ["Tag One", "Tag Two", "Tag Three"],
            "source_name": "Tech Crunch",
            "source_url": "https://techcrunch.com/article-2026",
            "original_content_hash": self.valid_hash,
            "automation_id": "n8n_san_exec_1",
            "generated_by_ai": True,
            "ai_model": "gpt-4o",
            "reviewer_model": "claude-3-5-sonnet",
            "review_decision": "approved",
            "quality_score": 96,
            "factual_accuracy_score": 98,
            "language_score": 95,
            "seo_score": 89
        }

    def test_allowed_html_formatting_and_links_sanitized_correctly(self):
        response = self.client.post("/api/blog/posts/", self.payload, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        post = BlogPost.objects.get(id=response.data["post_id"])
        self.assertIn("<h2>Artificial Intelligence Advancement in 2026</h2>", post.description)
        self.assertIn("<strong>Enhanced Efficiency:</strong>", post.description)
        self.assertIn('href="https://example.com/ai-report"', post.description)
        self.assertIn('rel="nofollow noopener noreferrer"', post.description)
        self.assertIn('target="_blank"', post.description)

    def test_scripts_styles_images_and_events_stripped(self):
        malicious_payload = self.payload.copy()
        malicious_payload["automation_id"] = "n8n_san_exec_2"
        malicious_payload["description"] = (
            "<h2>Clean Article Heading</h2>"
            "<script>alert('xss');</script>"
            "<style>body { background: red; }</style>"
            "<img src=\"https://evil.com/pic.jpg\" onerror=\"alert('hack')\" />"
            "<p style=\"color:blue;\" onclick=\"alert('click')\" data-track=\"123\">"
            "This paragraph contains more than 150 characters to ensure plain-text length validation passes cleanly. "
            "We are testing whether inline styles, event handlers, and data attributes are stripped out completely."
            "</p>"
        )

        response = self.client.post("/api/blog/posts/", malicious_payload, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        post = BlogPost.objects.get(id=response.data["post_id"])
        self.assertNotIn("<script>", post.description)
        self.assertNotIn("<style>", post.description)
        self.assertNotIn("<img", post.description)
        self.assertNotIn("onclick=", post.description)
        self.assertNotIn("onerror=", post.description)
        self.assertNotIn("style=", post.description)
        self.assertNotIn("data-track", post.description)
        self.assertIn("<p>This paragraph contains", post.description)

    def test_unsafe_javascript_link_rejected_with_422(self):
        unsafe_payload = self.payload.copy()
        unsafe_payload["automation_id"] = "n8n_san_exec_3"
        unsafe_payload["description"] = (
            "<h2>Unsafe Link Test Heading</h2>"
            "<p>Check out this article link: <a href=\"javascript:alert('xss')\">Click Here</a>. "
            "Adding sufficient text length so that short content validation does not trigger first in this test scenario.</p>"
        )

        response = self.client.post("/api/blog/posts/", unsafe_payload, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["code"], "AUTOMATION_CONTENT_INVALID")
        self.assertEqual(response.data["content_error"], "INVALID_LINK")

    def test_short_content_returns_422(self):
        short_payload = self.payload.copy()
        short_payload["automation_id"] = "n8n_san_exec_4"
        short_payload["description"] = "<p>Short content.</p>"

        response = self.client.post("/api/blog/posts/", short_payload, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["code"], "AUTOMATION_CONTENT_INVALID")
        self.assertEqual(response.data["content_error"], "ARTICLE_TOO_SHORT")

    @patch("blog_post.image_services.download_and_localize_automation_image")
    def test_sanitization_failure_prevents_image_download(self, mock_image_download):
        invalid_payload = self.payload.copy()
        invalid_payload["automation_id"] = "n8n_san_exec_5"
        invalid_payload["source_image_url"] = "https://example.com/image.jpg"
        invalid_payload["description"] = "<p>Too short</p>"

        response = self.client.post("/api/blog/posts/", invalid_payload, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(mock_image_download.called)


@override_settings(
    TECHLIFE_AUTOMATION_TOKEN="secret-tax-token-555",
    TECHLIFE_AUTOMATION_AUTHOR_USERNAME="techlife_desk"
)
class BlogPostAutomationTaxonomyResolutionTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Technology", slug="technology")
        self.subcategory = SubCategory.objects.create(category=self.category, name="Artificial Intelligence", slug="ai")

        self.other_cat = Category.objects.create(name="Health", slug="health")
        self.other_subcat = SubCategory.objects.create(category=self.other_cat, name="Fitness", slug="fitness")

        self.existing_tag = Tag.objects.create(name="Machine Learning", slug="machine-learning")

        self.client = APIClient()
        self.automation_user = User.objects.create_user(
            email="techlife_desk@techlifebd.com",
            password="Password123!",
            first_name="TechLife",
            last_name="Desk",
            is_active=True,
            is_staff=False,
            is_superuser=False
        )
        self.headers = {"HTTP_AUTHORIZATION": "Automation secret-tax-token-555"}
        self.valid_hash = "d" * 64

        self.valid_description = (
            "<h2>Taxonomy Resolution Test Article</h2>"
            "<p>This is a long valid article description containing more than 150 characters to pass length validation. "
            "We are testing category_slug, subcategory_slug, and tags_list resolution in automation requests.</p>"
        )

        self.payload = {
            "title": "Taxonomy Test Title",
            "description": self.valid_description,
            "category_slug": "technology",
            "subcategory_slug": "ai",
            "tags_list": ["#Machine Learning", "Deep Learning 2026", "Neural Networks"],
            "source_name": "TechCrunch",
            "source_url": "https://techcrunch.com/article-tax-1",
            "original_content_hash": self.valid_hash,
            "automation_id": "n8n_tax_exec_1",
            "generated_by_ai": True,
            "ai_model": "gpt-4o",
            "reviewer_model": "claude-3-5-sonnet",
            "review_decision": "approved",
            "quality_score": 95,
            "factual_accuracy_score": 99,
            "language_score": 94,
            "seo_score": 88
        }

    def test_successful_taxonomy_and_tag_resolution(self):
        response = self.client.post("/api/blog/posts/", self.payload, format='json', **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        post = BlogPost.objects.get(id=response.data["post_id"])
        self.assertEqual(post.category, self.category)
        self.assertEqual(post.subcategory, self.subcategory)
        self.assertEqual(post.tags.count(), 3)
        self.assertIn(self.existing_tag, post.tags.all())

    def test_unknown_category_returns_422(self):
        payload = self.payload.copy()
        payload["category_slug"] = "non-existent-category-999"
        response = self.client.post("/api/blog/posts/", payload, format='json', **self.headers)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["code"], "AUTOMATION_TAXONOMY_INVALID")
        self.assertEqual(response.data["taxonomy_error"], "UNKNOWN_CATEGORY")

    def test_subcategory_category_mismatch_returns_422(self):
        payload = self.payload.copy()
        payload["category_slug"] = "technology"
        payload["subcategory_slug"] = "fitness"  # belongs to Health, not Technology
        response = self.client.post("/api/blog/posts/", payload, format='json', **self.headers)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["code"], "AUTOMATION_TAXONOMY_INVALID")
        self.assertEqual(response.data["taxonomy_error"], "SUBCATEGORY_CATEGORY_MISMATCH")

    def test_direct_taxonomy_id_forbidden_returns_422(self):
        payload = self.payload.copy()
        payload["category_id"] = self.category.id
        response = self.client.post("/api/blog/posts/", payload, format='json', **self.headers)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["code"], "AUTOMATION_TAXONOMY_INVALID")
        self.assertEqual(response.data["taxonomy_error"], "DIRECT_TAXONOMY_ID_FORBIDDEN")

    def test_too_few_tags_returns_422(self):
        payload = self.payload.copy()
        payload["tags_list"] = ["Tag1", "Tag2"]  # only 2 tags
        response = self.client.post("/api/blog/posts/", payload, format='json', **self.headers)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["taxonomy_error"], "TOO_FEW_TAGS")

    def test_too_many_new_tags_returns_422(self):
        payload = self.payload.copy()
        payload["tags_list"] = ["NewTag1", "NewTag2", "NewTag3", "NewTag4"]  # 4 new tags
        response = self.client.post("/api/blog/posts/", payload, format='json', **self.headers)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["taxonomy_error"], "TOO_MANY_NEW_TAGS")

    def test_reserved_tag_returns_422(self):
        payload = self.payload.copy()
        payload["tags_list"] = ["Machine Learning", "Deep Learning", "news"]
        response = self.client.post("/api/blog/posts/", payload, format='json', **self.headers)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["taxonomy_error"], "RESERVED_TAG")


from django.conf import settings
from blog_post.models import AutomationPublishLog
from blog_post.automation_services import get_asia_dhaka_day_range
from datetime import timedelta
import zoneinfo


class AutomationGuardrailTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Tech", slug="tech")
        self.subcategory = SubCategory.objects.create(name="AI", slug="ai", category=self.category)
        self.existing_tag = Tag.objects.create(name="Automation", slug="automation")
        Tag.objects.create(name="Deep Learning", slug="deep-learning")
        Tag.objects.create(name="Neural Nets", slug="neural-nets")

        self.automation_user = User.objects.create_user(
            email="techlife_desk@techlifebd.com",
            password="securepassword123",
            first_name="TechLife",
            last_name="Desk",
            is_active=True,
            is_staff=False,
            is_superuser=False
        )

        self.staff_user = User.objects.create_user(
            email="admin_staff@techlifebd.com",
            password="staffpassword123",
            first_name="Admin",
            last_name="Staff",
            is_active=True,
            is_staff=True,
            is_superuser=True
        )

        self.valid_hash = "a" * 64
        self.valid_description = (
            "<h2>Comprehensive AI Article</h2><p>This is a long valid article description containing more than 150 characters to pass length validation. "
            "It provides clear insights and detailed analysis on modern technology trends, software development, and digital transformation in 2026.</p>"
        )

        self.valid_payload = {
            "title": "Guardrail Test Article Title",
            "description": self.valid_description,
            "category_slug": self.category.slug,
            "tags_list": ["Tag Alpha", "Tag Beta", "Tag Gamma"],
            "source_name": "TechCrunch",
            "source_url": "https://techcrunch.com/2026/08/18/ai-breakthrough",
            "original_content_hash": self.valid_hash,
            "automation_id": "auto_guard_100",
            "generated_by_ai": True,
            "ai_model": "gpt-4o",
            "reviewer_model": "claude-3-5-sonnet",
            "review_decision": "approved",
            "quality_score": 95,
            "factual_accuracy_score": 98,
            "language_score": 92,
            "seo_score": 85,
            "review_notes": "All facts verified."
        }

        self.token = "valid_test_automation_token_123"
        settings.TECHLIFE_AUTOMATION_TOKEN = self.token
        settings.TECHLIFE_AUTOMATION_AUTHOR_USERNAME = "techlife_desk"
        settings.TECHLIFE_AUTOMATION_ENABLED = True
        settings.TECHLIFE_AUTOMATION_DAILY_POST_LIMIT = 4
        settings.TECHLIFE_AUTOMATION_HOURLY_REQUEST_LIMIT = 20
        settings.TECHLIFE_AUTOMATION_TIMEZONE = "Asia/Dhaka"

        self.headers = {
            "HTTP_AUTHORIZATION": f"Automation {self.token}"
        }

    def test_automation_disabled_returns_503(self):
        settings.TECHLIFE_AUTOMATION_ENABLED = False
        response = self.client.post("/api/blog/posts/", self.valid_payload, format='json', **self.headers)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["status"], "disabled")
        self.assertEqual(response.data["code"], "AUTOMATION_DISABLED")

        # Verify audit log recorded disabled event
        log = AutomationPublishLog.objects.filter(automation_id="auto_guard_100").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.event_type, "disabled")
        self.assertEqual(log.http_status, 503)

    def test_daily_four_post_limit_enforced(self):
        # Create 4 published logs today in Asia/Dhaka
        local_start, local_end = get_asia_dhaka_day_range()
        for i in range(4):
            AutomationPublishLog.objects.create(
                automation_id=f"auto_pub_{i}",
                event_type="published",
                http_status=201,
                result_code="AUTOMATION_POST_PUBLISHED"
            )

        # 5th request should be throttled by 4-post daily limit
        response = self.client.post("/api/blog/posts/", self.valid_payload, format='json', **self.headers)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data["status"], "throttled")
        self.assertEqual(response.data["code"], "DAILY_PUBLISH_LIMIT_REACHED")
        self.assertEqual(response.data["daily_limit"], 4)
        self.assertEqual(response.data["published_today"], 4)

    def test_rejected_requests_do_not_count_towards_daily_limit(self):
        # Create 3 published logs and 5 rejected logs today
        for i in range(3):
            AutomationPublishLog.objects.create(
                automation_id=f"pub_{i}",
                event_type="published",
                http_status=201,
            )
        for i in range(5):
            AutomationPublishLog.objects.create(
                automation_id=f"rej_{i}",
                event_type="rejected",
                http_status=422,
            )

        # 4th valid request should publish successfully (because rejected logs don't count)
        response = self.client.post("/api/blog/posts/", self.valid_payload, format='json', **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "published")

    def test_idempotent_replay_does_not_consume_quota(self):
        # Publish first post successfully
        resp1 = self.client.post("/api/blog/posts/", self.valid_payload, format='json', **self.headers)
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        post_id = resp1.data["post_id"]

        # Fill remaining 3 quota slots with published logs
        for i in range(3):
            AutomationPublishLog.objects.create(
                automation_id=f"slot_{i}",
                event_type="published",
                http_status=201,
            )

        # Retrying the first request (existing automation_id) should return HTTP 200 replay even though daily limit is full
        resp_retry = self.client.post("/api/blog/posts/", self.valid_payload, format='json', **self.headers)
        self.assertEqual(resp_retry.status_code, status.HTTP_200_OK)
        self.assertTrue(resp_retry.data["idempotent_replay"])
        self.assertEqual(resp_retry.data["post_id"], post_id)

    def test_manual_posts_excluded_from_automation_limit(self):
        # Create 10 manual posts created via standard ORM / UI views
        for i in range(10):
            BlogPost.objects.create(
                title=f"Manual Post {i}",
                slug=f"manual-post-{i}",
                description="Manual post content",
                category=self.category,
                subcategory=self.subcategory,
                author=self.staff_user,
                status="published"
            )

        # Automation endpoint should still allow publishing up to daily_limit (4)
        response = self.client.post("/api/blog/posts/", self.valid_payload, format='json', **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_hourly_throttle_enforced(self):
        # Create 20 request logs in the last 30 minutes
        for i in range(20):
            AutomationPublishLog.objects.create(
                automation_id=f"hourly_{i}",
                event_type="request_received",
                http_status=422,
            )

        # 21st request within the hour should be rate limited
        response = self.client.post("/api/blog/posts/", self.valid_payload, format='json', **self.headers)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data["code"], "AUTOMATION_REQUEST_RATE_LIMITED")

    def test_bangladesh_midnight_boundary_resets_quota(self):
        local_start, local_end = get_asia_dhaka_day_range()
        yesterday_dt = local_start - timedelta(hours=2)

        # Create 4 published logs yesterday in Asia/Dhaka
        for i in range(4):
            log = AutomationPublishLog.objects.create(
                automation_id=f"yest_{i}",
                event_type="published",
                http_status=201,
            )
            log.created_at = yesterday_dt
            log.save()

        # Today's new request should succeed (201) because quota reset at Dhaka midnight
        response = self.client.post("/api/blog/posts/", self.valid_payload, format='json', **self.headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_log_privacy_and_secret_non_storage(self):
        # Send a request with authorization header and sensitive string in error
        payload = self.valid_payload.copy()
        payload["quality_score"] = 50  # Fail gate to trigger log entry

        self.client.post("/api/blog/posts/", payload, format='json', **self.headers)

        log = AutomationPublishLog.objects.order_by('-created_at').first()
        self.assertIsNotNone(log)
        # Ensure secret token / Authorization headers are NOT saved in database log
        self.assertNotIn(self.token, log.error_summary)
        self.assertNotIn("Authorization", log.error_summary)

    def test_dashboard_overview_access_and_cotton_rendering(self):
        self.client.force_login(self.staff_user)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("automation_ops", response.context)
        self.assertEqual(response.context["automation_ops"]["daily_limit"], 4)
        self.assertContains(response, "Automation Operations")

    def test_public_non_exposure(self):
        # Ensure public post list API does NOT expose AutomationPublishLog fields or logs
        response = self.client.get("/api/blog/posts/")
        self.assertEqual(response.status_code, 200)
        content_str = str(response.content)
        self.assertNotIn("AutomationPublishLog", content_str)
        self.assertNotIn("error_summary", content_str)


class CanonicalSearchResultsViewTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            email="quantum_author@techlifebd.com",
            password="Password123!",
            first_name="Quantum",
            last_name="Author"
        )
        self.user2 = User.objects.create_user(
            email="web_author@techlifebd.com",
            password="Password123!",
            first_name="Alice",
            last_name="Smith"
        )
        self.category = Category.objects.create(name="Artificial Intelligence", slug="ai-tech")
        self.sub_category = SubCategory.objects.create(name="Deep Learning", slug="deep-learning", category=self.category)
        self.tag = Tag.objects.create(name="neural-networks", slug="neural-networks")

        self.post1 = BlogPost.objects.create(
            title="Quantum Computing breakthrough in 2026",
            subtitle="Quantum algorithms explained",
            description="Detailed article on quantum processors",
            author=self.user1,
            category=self.category,
            subcategory=self.sub_category,
            status="published"
        )
        self.post1.tags.add(self.tag)

        self.post2 = BlogPost.objects.create(
            title="Web Development Best Practices",
            subtitle="Frontend frameworks overview",
            description="Guide to modern UI development",
            author=self.user2,
            category=self.category,
            status="published"
        )

    def test_search_by_title_returns_results_page(self):
        url = reverse("redirect_search_results") + "?q=Quantum"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Quantum Computing breakthrough")
        self.assertNotContains(response, "Web Development Best Practices")

    def test_search_by_category_and_tag(self):
        url = reverse("redirect_search_results") + "?q=neural-networks"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Quantum Computing breakthrough")

    def test_search_by_author(self):
        url = reverse("redirect_search_results") + "?q=Quantum"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Quantum")

    def test_htmx_partial_search_request(self):
        url = reverse("redirect_search_results") + "?q=Quantum"
        headers = {"HTTP_HX_REQUEST": "true"}
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "components/search/partial_search_results.html")

    def test_empty_query_returns_search_page(self):
        url = reverse("redirect_search_results") + "?q="
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)







