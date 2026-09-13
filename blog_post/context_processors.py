from django.shortcuts import render , redirect , get_object_or_404
from forum.models import Follow_section
from blog_post.models import Category
from contact.models import FooterSettings
from site_settings.models import SiteSettings

def all_category(request):
    from django.db.models import Count
    popular_categories = Category.objects.prefetch_related('subcategories').annotate(
        sub_count=Count('subcategories')
    ).order_by('-sub_count', 'name')
    context = {
        "popular_categories": popular_categories,
    }
    return(context) 
    
from datetime import datetime

def timezone_info(request):
    now = datetime.now()
    formatted_date = now.strftime("%A, %B %d, %Y")
    from django.db.models import Count
    categories = Category.objects.prefetch_related('subcategories').annotate(
        sub_count=Count('subcategories')
    ).order_by('-sub_count', 'name')
    
    return{
        'current_date': formatted_date,
        "categories": categories
    }

def footer_context(request):
    return {
        'footer': FooterSettings.objects.first(),
        'site_settings': SiteSettings.objects.first()
    }

def follow_stats(request):

    if request.user.is_authenticated and getattr(request.user, 'is_verified', False):
        follow_data, created = Follow_section.objects.get_or_create(user=request.user)
        return {
            'user_follow_stats': follow_data
        }
    
    return {
        'user_follow_stats': None
    }


def trending_news(request):
    from blog_post.models import BlogPost
    try:
        posts = list(
            BlogPost.objects.filter(status="published")
            .select_related("category", "author")
            .order_by("-created_at")[:10]
        )
    except Exception:
        posts = []
    return {
        'trending_news_list': posts,
        'recent_news_list': posts[:10],
    }



    