import os
import django
import random
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings.local')
django.setup()

from blog_post.models import BlogPost
from dashboard.models import DailyPostStat
from django.contrib.auth import get_user_model

# Clear existing traffic stats
DailyPostStat.objects.all().delete()

posts = list(BlogPost.objects.all())
if not posts:
    User = get_user_model()
    user = User.objects.first()
    if user:
        post = BlogPost.objects.create(title="Dummy Post for Traffic", author=user, content="<p>Test</p>", status="published")
        posts = [post]
        print("Created a dummy post.")

if not posts:
    print("No users or posts found. Cannot generate traffic.")
    exit()

today = timezone.now().date()
total_views = 0

print("Generating realistic traffic data for the last 95 days...")

for i in range(95):
    date = today - timedelta(days=94 - i)
    
    # Weekly seasonality: weekends have less traffic
    is_weekend = date.weekday() >= 5
    base_traffic = 35 if is_weekend else 85
    
    # Organic Growth trend
    growth_factor = i / 94.0 
    
    daily_total = int(base_traffic * (1 + growth_factor * 1.5) + random.randint(-15, 45))
    daily_total = max(10, daily_total)
    
    sampled_posts = random.sample(posts, min(5, len(posts)))
    
    for post in sampled_posts:
        views_for_post = daily_total // len(sampled_posts) + random.randint(0, 8)
        DailyPostStat.objects.create(
            post=post,
            date=date,
            views_count=views_for_post
        )
        total_views += views_for_post

print(f"Successfully generated 95 days of realistic traffic data! Total visits: {total_views}")
