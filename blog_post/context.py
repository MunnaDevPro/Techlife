from blog_post.models import Category
from django.db.models import Count

def navbar_all_categorie(request):
    return {
        'categories': Category.objects.prefetch_related('subcategories').annotate(
            sub_count=Count('subcategories')
        ).order_by('-sub_count', 'name')
    }
