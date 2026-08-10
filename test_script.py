from blog_post.models import BlogPost
from accounts.models import CustomUserModel

author = CustomUserModel.objects.first()
post = BlogPost.objects.create(title='Test Pending Post 2', description='This is a test post', author=author, status='pending')
print("Created post ID:", post.id)
