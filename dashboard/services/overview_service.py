from django.core.cache import cache
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from blog_post.models import BlogPost
from accounts.models import CustomUserModel
from forum.models import Question, Answer
from contact.models import contact_or_support
from comments.models import Comment

def get_kpi_counts():
    """
    Returns real counts for the KPI cards.
    Caches results for 60 seconds.
    """
    def _fetch():
        total_published = BlogPost.objects.filter(status="published").count()
        pending_review = BlogPost.objects.filter(status__in=["pending", "edited"]).count()
        total_verified_users = CustomUserModel.objects.filter(is_verified=True).count()
        total_unverified_users = CustomUserModel.objects.filter(is_verified=False).count()
        # Active reports/flags (fall back to contact_or_support as proxy since no specific report model exists)
        active_reports = contact_or_support.objects.count()
        total_questions = Question.objects.count()
        total_answers = Answer.objects.count()
        
        return {
            "total_published_posts": total_published,
            "pending_review_count": pending_review,
            "total_verified_users": total_verified_users,
            "total_unverified_users": total_unverified_users,
            "active_reports_count": active_reports,
            "total_forum_questions": total_questions,
            "total_forum_answers": total_answers,
        }
    
    return cache.get_or_set("dashboard_kpi_counts", _fetch, 60)

def get_posts_chart_data():
    """
    Computes count of published posts per day for the last 30 days.
    Caches the result for 5 minutes (300 seconds).
    Note: Production setups should configure a Redis cache backend.
    """
    def _fetch():
        today = timezone.now().date()
        start_date = today - timedelta(days=29)
        
        queryset = (
            BlogPost.objects.filter(status="published", created_at__date__gte=start_date)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        
        date_counts = {item['date']: item['count'] for item in queryset if item['date']}
        labels = []
        values = []
        
        # Populate each day to ensure a smooth, continuous line with no gaps
        for i in range(30):
            d = start_date + timedelta(days=i)
            labels.append(d.strftime('%b %d'))
            values.append(date_counts.get(d, 0))
            
        return {
            "labels": labels,
            "values": values,
        }
        
    return cache.get_or_set("dashboard_posts_chart_data", _fetch, 300)

def get_forum_chart_data():
    """
    Computes count of forum questions and answers per day for the last 30 days.
    Caches the result for 5 minutes (300 seconds).
    """
    def _fetch():
        today = timezone.now().date()
        start_date = today - timedelta(days=29)
        
        questions_qs = (
            Question.objects.filter(created_at__date__gte=start_date)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        
        answers_qs = (
            Answer.objects.filter(created_at__date__gte=start_date)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        
        question_counts = {item['date']: item['count'] for item in questions_qs if item['date']}
        answer_counts = {item['date']: item['count'] for item in answers_qs if item['date']}
        
        labels = []
        question_values = []
        answer_values = []
        
        for i in range(30):
            d = start_date + timedelta(days=i)
            labels.append(d.strftime('%b %d'))
            question_values.append(question_counts.get(d, 0))
            answer_values.append(answer_counts.get(d, 0))
            
        return {
            "labels": labels,
            "question_values": question_values,
            "answer_values": answer_values,
        }
        
    return cache.get_or_set("dashboard_forum_chart_data", _fetch, 300)


def get_posts_by_category():
    """
    Computes count of published posts grouped by category.
    """
    def _fetch():
        queryset = (
            BlogPost.objects.filter(status="published")
            .exclude(category__isnull=True)
            .values('category__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5] # Top 5 categories
        )
        
        labels = [item['category__name'] for item in queryset]
        values = [item['count'] for item in queryset]
        
        return {
            "labels": labels,
            "values": values,
        }
        
    return cache.get_or_set("dashboard_posts_by_category", _fetch, 300)

def get_user_stats():
    """
    Computes user breakdown (Verified vs Unverified).
    """
    def _fetch():
        verified = CustomUserModel.objects.filter(is_verified=True).count()
        unverified = CustomUserModel.objects.filter(is_verified=False).count()
        
        return {
            "labels": ["Verified", "Unverified"],
            "values": [verified, unverified],
        }
        
    return cache.get_or_set("dashboard_user_stats", _fetch, 300)

def get_recent_activity():
    """
    Pulls recent activities (published posts, verified users, recent comments).
    Combines and orders them by recency, returning top 10 items.
    Caches results for 60 seconds.
    """
    def _fetch():
        # Retrieve recent items using select_related to prevent N+1 queries
        posts = BlogPost.objects.filter(status="published").select_related('author').order_by('-created_at')[:10]
        users = CustomUserModel.objects.filter(is_verified=True).order_by('-created_at')[:10]
        comments = Comment.objects.select_related('user', 'post').order_by('-created_at')[:10]
        
        events = []
        for p in posts:
            events.append({
                "type": "post_published",
                "title": "Post Published",
                "description": f'"{p.title}" was published by {p.author.email if p.author else "System"}',
                "timestamp": p.created_at,
                "icon": "file-text",
            })
        for u in users:
            events.append({
                "type": "user_verified",
                "title": "User Verified",
                "description": f"User {u.email} has been verified",
                "timestamp": u.created_at,
                "icon": "user-check",
            })
        for c in comments:
            events.append({
                "type": "comment_added",
                "title": "New Comment",
                "description": f'Comment by {c.user.email if c.user else "Anonymous"} on "{c.post.title if c.post else "Deleted Post"}"',
                "timestamp": c.created_at,
                "icon": "message-square",
            })
            
        # Sort combined list by timestamp in descending order and slice top 10
        events.sort(key=lambda x: x["timestamp"], reverse=True)
        return events[:10]
        
    return cache.get_or_set("dashboard_recent_activity", _fetch, 60)
