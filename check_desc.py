import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Techlife.settings')
django.setup()
from blog_post.models import BlogPost
posts = BlogPost.objects.filter(status='published')[:3]
for p in posts:
    print('---')
    print('title:', p.title[:60])
    print('description:', (p.description or '')[:200])
    print('meta_description:', (p.meta_description or '')[:200])
    print('subtitle:', p.subtitle)
