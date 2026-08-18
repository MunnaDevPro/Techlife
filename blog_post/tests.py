from django.test import TestCase, override_settings
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse

from blog_post.models import BlogPost, Category
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
            "description": "Automated post content generated by n8n workflow",
            "category": self.category.id,
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
            "author_id": other_user.id
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
            "description": "High quality AI generated article passing all approval gates.",
            "category": self.category.id,
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


