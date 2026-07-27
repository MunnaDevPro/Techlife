from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Count
from blog_post.models import BlogPost, Like, Post_view_ip
from comments.models import Comment
from dashboard.models import DailyPostStat

def compute_daily_rollup(target_date=None):
    """
    Aggregates real views, likes, and comments per post on a given target_date (defaults to yesterday),
    and upserts into the DailyPostStat rollup table.
    """
    if target_date is None:
        target_date = timezone.now().date() - timedelta(days=1)
        
    posts = BlogPost.objects.all()
    
    # Query views for target_date
    views_by_post = {
        item['post_id']: item['count']
        for item in Post_view_ip.objects.filter(viewed_at=target_date)
        .values('post_id')
        .annotate(count=Count('id'))
    }
    
    # Query likes for target_date
    likes_by_post = {
        item['post_id']: item['count']
        for item in Like.objects.filter(created_at__date=target_date)
        .values('post_id')
        .annotate(count=Count('id'))
    }
    
    # Query comments for target_date
    comments_by_post = {
        item['post_id']: item['count']
        for item in Comment.objects.filter(created_at__date=target_date)
        .values('post_id')
        .annotate(count=Count('id'))
    }
    
    upserted_count = 0
    with transaction.atomic():
        for post in posts:
            v_count = views_by_post.get(post.id, 0)
            l_count = likes_by_post.get(post.id, 0)
            c_count = comments_by_post.get(post.id, 0)
            
            # Upsert rollup statistics
            if v_count > 0 or l_count > 0 or c_count > 0:
                DailyPostStat.objects.update_or_create(
                    post=post,
                    date=target_date,
                    defaults={
                        'views_count': v_count,
                        'likes_count': l_count,
                        'comments_count': c_count,
                    }
                )
                upserted_count += 1
                
    return upserted_count
