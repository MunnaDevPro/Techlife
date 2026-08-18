from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from blog_post.models import BlogPost, Category
from blog_post.forms import BlogPostForm
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
