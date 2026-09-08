from django.shortcuts import render , redirect , get_object_or_404
from forum.models import Follow_section
from blog_post.models import Category
from contact.models import FooterSettings
from site_settings.models import SiteSettings

def all_category(request):
    popular_categories = Category.objects.all().order_by('created_at')
    context = {
        "popular_categories": popular_categories,
    }
    return(context) 
    
from datetime import datetime

def timezone_info(request):
    
    now = datetime.now()
    

    formatted_date = now.strftime("%A, %B %d, %Y")
    
    return{
        'current_date': formatted_date,
        "categories": Category.objects.all()
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

    