import django_filters
from blog_post.models import BlogPost, Category
from django.db.models import Q

class BlogPostFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=BlogPost.STATUS_CHOICES, empty_label="All Statuses")
    category = django_filters.ModelChoiceFilter(queryset=Category.objects.all(), empty_label="All Categories")
    author = django_filters.CharFilter(method='filter_author', label="Author Search")
    search = django_filters.CharFilter(method='filter_search', label="Search")
    
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte', label='From Date')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte', label='To Date')

    class Meta:
        model = BlogPost
        fields = ['status', 'category']

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value) |
            Q(summary__icontains=value) |
            Q(content__icontains=value)
        )

    def filter_author(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(author__email__icontains=value) |
            Q(author__first_name__icontains=value) |
            Q(author__last_name__icontains=value)
        )
