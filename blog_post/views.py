from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.db.models import Count, F
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.db.models import Q
from .models import BlogPost, Category, Review, SubCategory
from .models import BlogPost, BlogAdditionalImage, Category, Tag
from .forms import BlogPostForm
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from django.db import IntegrityError
from .models import BlogPost, Like

from accounts.models import CustomUserModel

from comments.models import Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.views.decorators.http import require_POST
from django.contrib import messages
from blog_post.models import BlogPost, compnay_logo
from comments.models import Comment, Reply

from .homepage_helpers import get_carousel_posts, get_homepage_config, get_section_posts

from interactions.models import Share
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from blog_post.models import Post_view_ip
from zlib import crc32


# IP Tracking
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


BLOG_LIST_ONLY_FIELDS = (
    "id",
    "title",
    "subtitle",
    "slug",
    "featured_image",
    "featured_image_url",
    "created_at",
    "status",
    "views",
    "author__email",
    "category__name",
    "category__slug",
    "category__font_awesome_icon",
)


def published_posts_queryset():
    return (
        BlogPost.objects.select_related("author", "category")
        .prefetch_related("tags")
        .only(*BLOG_LIST_ONLY_FIELDS)
        .filter(status="published")
    )


def get_display_views(post):
    # Stable pseudo-random baseline in [2000, 5000] so the displayed value
    # remains smooth across refreshes while real views still grow naturally.
    baseline = 2000 + (crc32(post.slug.encode("utf-8")) % 3001)
    return post.views + baseline


def get_display_link_count(post):
    # Stable pseudo-random baseline in [1000, 4000] + real likes.
    baseline = 1000 + (crc32(f"{post.slug}-link".encode("utf-8")) % 3001)
    return baseline + post.likes.count()


def get_display_like_count(post):
    # Stable pseudo-random baseline in [1000, 4000] + real likes.
    baseline = 1000 + (crc32(f"{post.slug}-like".encode("utf-8")) % 3001)
    return baseline + post.likes.count()


def blog_details_view(request, slug):
    blog_detail = (
        BlogPost.objects.select_related("category", "author")
        .prefetch_related("reviews", "additional_images", "tags", "likes")
        .get(slug=slug, status="published")
    )

    related_news = BlogPost.objects.filter(
        status="published", category=blog_detail.category
    ).exclude(slug=slug)[:10]

    if blog_detail.description:
        word_count = len(blog_detail.description.split())
    else:
        word_count = 0

    most_viewed_blogs = BlogPost.objects.filter(status="published").order_by("-views")[:15]

    all_comments = (
        Comment.objects
        .filter(post=blog_detail)
        .select_related("user", "post")
        .prefetch_related("replies__user")
        .order_by("-created_at")
    )

    comment_count = all_comments.count()
    reply_count = sum(comment.replies.count() for comment in all_comments)
    total_comments = comment_count + reply_count

    paginator = Paginator(all_comments, 3)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except Exception:
        page_obj = paginator.page(paginator.num_pages)

    sort_by = request.GET.get('sort_by', 'newest')
    comment_order = '-created_at'
    if sort_by == 'oldest':
        comment_order = 'created_at'
    elif sort_by == 'recent':
        comment_order = '-updated_at'

    all_comments = Comment.objects.filter(post=blog_detail).order_by(comment_order)

    # Like check
    user_has_liked = False
    if request.user.is_authenticated:
        try:
            Like.objects.get(post=blog_detail, user=request.user)
            user_has_liked = True
        except Like.DoesNotExist:
            user_has_liked = False

    # View count via IP
    ip = get_client_ip(request)
    if request.user.is_authenticated:
        viewed = Post_view_ip.objects.filter(post=blog_detail, user=request.user).exists()
        if not viewed:
            Post_view_ip.objects.create(post=blog_detail, user=request.user)
            blog_detail.views += 1
            blog_detail.save()
    else:
        viewed = Post_view_ip.objects.filter(post=blog_detail, ip_address=ip).exists()
        if not viewed:
            Post_view_ip.objects.create(post=blog_detail, ip_address=ip)
            blog_detail.views += 1
            blog_detail.save()

    context = {
        "blog_detail":    blog_detail,
        "post":           blog_detail,
        "display_views":  get_display_views(blog_detail),
        "display_link_count": get_display_link_count(blog_detail),
        "display_like_count": get_display_like_count(blog_detail),
        "related_news":   related_news,
        "word_count":     word_count,
        "most_viewed_blogs": most_viewed_blogs,
        "all_comments":   page_obj,
        "total_comments": total_comments,
        "user_has_liked": user_has_liked,
        "sort_by":        sort_by,
        "action":         "blog_details",
    }

    if request.headers.get("HX-Request"):
        return render(request, "components/blog_details/partial_blog_details_page.html", context)
    return render(request, "components/blog_details/blog_details_page.html", context)


@vary_on_headers("HX-Request")
def home(request):
    published_posts = published_posts_queryset()

    carousel_blogs = get_carousel_posts()

    blogs = get_section_posts("blog_grid", default_count=8)

    latest_blogs = get_section_posts("latest_news", default_count=8)
    if not latest_blogs:
        latest_blogs = list(published_posts.order_by("-created_at")[:8])

    latest_blog = latest_blogs[0] if latest_blogs else None
    Only_latest_blogs = latest_blogs[:1]
    latest_popular_blogs = latest_blogs

    most_viewed_blogs = get_section_posts(
        "most_viewed",
        default_count=8,
        order_by="-views",
    )

    fallback_top_categories = list(
        Category.objects.annotate(
            post_count=Count("blogpost")
        ).filter(post_count__gt=0).order_by("-post_count")[:6]
    )

    cat1_config = get_homepage_config("cat_section_1")
    cat2_config = get_homepage_config("cat_section_2")
    cat3_config = get_homepage_config("cat_section_3")

    def _fallback_category(index):
        return fallback_top_categories[index] if len(fallback_top_categories) > index else None

    first_category = (
        cat1_config.category if cat1_config and cat1_config.category else _fallback_category(0)
    )
    second_category = (
        cat2_config.category if cat2_config and cat2_config.category else _fallback_category(1)
    )
    third_category = (
        cat3_config.category if cat3_config and cat3_config.category else _fallback_category(2)
    )

    top_categories = [
        category
        for category in (first_category, second_category, third_category)
        if category
    ]

    def _category_posts(section_key, config, category, default_count=6):
        if config and config.category:
            return get_section_posts(section_key, default_count=default_count)
        count = config.post_count if config else default_count
        if not category:
            return []
        return list(
            published_posts.filter(category=category).order_by("-created_at")[:count]
        )

    cat1_blogs = _category_posts("cat_section_1", cat1_config, first_category, default_count=6)
    cat2_blogs = _category_posts("cat_section_2", cat2_config, second_category, default_count=6)
    cat3_blogs = _category_posts("cat_section_3", cat3_config, third_category, default_count=6)

    first_blogs = cat1_blogs
    second_blogs = cat2_blogs
    third_blogs = cat3_blogs

    all_category = Category.objects.all()

    top_users = (
        CustomUserModel.objects
        .filter(is_verified=True, is_superuser=False)
        .annotate(post_count=Count('authored_posts'))
        .filter(post_count__gt=0)
        .order_by('-post_count')[:4]
    )

    tech_cat = Category.objects.filter(slug='technology').first()
    technology_posts = published_posts.filter(
        category__slug="technology"
    ).order_by("-created_at")[:4]

    news_cat = Category.objects.filter(slug='news').first()
    news_posts = published_posts.filter(
        category__slug="news"
    ).order_by("-created_at")[:4]

    tips_cat = Category.objects.filter(slug='tips-tricks').first()
    tips_posts = published_posts.filter(
        category__slug="tips-tricks"
    ).order_by("-created_at")[:4]

    popular_categories = (
        Category.objects
        .annotate(
            published_post_count=Count(
                'blogpost',
                filter=Q(blogpost__status='published')
            )
        )
        .filter(published_post_count__gt=0)
        .order_by('-published_post_count')[:7]
    )

    popular_posts_flat_list = []
    for category in popular_categories:
        latest_post = published_posts.filter(category=category).order_by("-created_at")[:1]
        if latest_post:
            post = latest_post[0]
            popular_posts_flat_list.append({
                'title':            post.title,
                'created_at':       post.created_at,
                'slug':             post.slug,
                'views':            post.views,
                'author_username':  post.author.email,
                'category_name':    category.name,
                'category_icon':    category.font_awesome_icon,
                'featured_image':   post.featured_image,
                'featured_image_url': post.featured_image_url,
            })

    news__related_posts = published_posts.filter(
        category__slug="news"
    ).order_by("-views", "-likes", "-created_at")

    Teacnology_related_posts = published_posts.filter(
        category__slug="technology"
    ).order_by("-views", "-likes", "-created_at")

    programming_related_posts = published_posts.filter(
        category__slug="programming"
    ).order_by("-views", "-likes", "-created_at")

    logos    = compnay_logo.objects.all()
    top_tags = Tag.objects.annotate(num_posts=Count('blog_posts')).order_by('-num_posts')

    context = {
        "first_category":   first_category,
        "second_category":  second_category,
        "third_category":   third_category,
        "tech_cat":         tech_cat,
        "news_cat":         news_cat,
        "tips_cat":         tips_cat,
        "first_blogs":      first_blogs,
        "second_blogs":     second_blogs,
        "third_blogs":      third_blogs,
        "cat1_blogs":       cat1_blogs,
        "cat2_blogs":       cat2_blogs,
        "cat3_blogs":       cat3_blogs,
        "blogs":            blogs,
        "latest_blog":      latest_blog,
        "latest_blogs":     latest_blogs,
        "top_users":        top_users,
        "carousel_blogs":   carousel_blogs,
        "top_tags":         top_tags,
        "technology_posts": technology_posts,
        "news_posts":       news_posts,
        "tips_posts":       tips_posts,
        "Only_latest_blogs":       Only_latest_blogs,
        "latest_popular_blogs":    latest_popular_blogs,
        "popular_posts_flat_list": popular_posts_flat_list,
        "news__related_posts":     news__related_posts,
        "Teacnology_related_posts":   Teacnology_related_posts,
        "programming_related_posts":  programming_related_posts,
        "most_viewed_blogs": most_viewed_blogs,
        "all_category":     all_category,
        "logos":            logos,
        "top_categories":   top_categories,
        "action":           "home_page",
    }

    if request.headers.get("HX-Request"):
        return render(request, "components/home/partial_homepage.html", context)
    return render(request, "home.html", context)


def redirect_search_results(request):
    query = request.GET.get('q', '').strip()

    if not query:
        context = {
            "query": "",
            "blogs": [],
            "total_blogs": 0,
            "categories": Category.objects.all(),
            "action": "search_results",
        }
        if request.headers.get("HX-Request"):
            return render(request, "components/search/partial_search_results.html", context)
        return render(request, "components/search/search_results.html", context)

    search_filter = (
        Q(title__icontains=query) |
        Q(subtitle__icontains=query) |
        Q(description__icontains=query) |
        Q(tags__name__icontains=query) |
        Q(category__name__icontains=query) |
        Q(subcategory__name__icontains=query) |
        Q(author__first_name__icontains=query) |
        Q(author__last_name__icontains=query) |
        Q(author__email__icontains=query)
    )

    published_posts = (
        BlogPost.objects.filter(status="published")
        .select_related("author", "category", "subcategory")
        .prefetch_related("tags")
        .filter(search_filter)
        .distinct()
        .order_by("-created_at")
    )

    total_count = published_posts.count()

    paginator = Paginator(published_posts, 12)
    page_number = request.GET.get('page', 1)
    try:
        blogs_page = paginator.page(page_number)
    except PageNotAnInteger:
        blogs_page = paginator.page(1)
    except EmptyPage:
        blogs_page = paginator.page(paginator.num_pages)

    categories = Category.objects.all()

    context = {
        "query": query,
        "blogs": blogs_page,
        "total_blogs": total_count,
        "categories": categories,
        "action": "search_results",
    }

    if request.headers.get("HX-Request"):
        return render(request, "components/search/partial_search_results.html", context)
    return render(request, "components/search/search_results.html", context)


@vary_on_headers("HX-Request")
def all_blog_post_view(request):
    published_posts = published_posts_queryset()

    blogs      = published_posts.order_by("-created_at")
    categories = Category.objects.all()

    author_email = request.GET.get("author")
    if author_email:
        blogs = blogs.filter(author__email=author_email)

    paginator    = Paginator(blogs, 12)
    page_number  = request.GET.get('page')
    blogs        = paginator.get_page(page_number)

    context = {
        "blogs":      blogs,
        "categories": categories,
        "filtered_author": author_email,
        "action":     "all_blogs",
    }

    if request.headers.get("HX-Request"):
        return render(request, "components/blogs/partial_all_blog_page.html", context)
    return render(request, "components/blogs/all_blog_page.html", context)


@vary_on_headers("HX-Request")
def popular_blog_post(request):
    popular_blogs_list = (
        published_posts_queryset()
        .filter(views__gte=1000)
        .order_by("-views", "-created_at")
        .distinct()
    )

    paginator = Paginator(popular_blogs_list, 12)
    page = request.GET.get('page')

    try:
        blogs = paginator.page(page)
    except PageNotAnInteger:
        blogs = paginator.page(1)
    except EmptyPage:
        blogs = paginator.page(paginator.num_pages)

    context = {
        "popular_blogs": blogs,
    }

    if request.headers.get("HX-Request"):
        return render(request, "components/popular/popular_post_partial.html", context)
    return render(request, "components/popular/popular_post.html", context)


def all_article(request):
    published_posts = published_posts_queryset()
    blogs      = published_posts
    categories = Category.objects.all()

    sidebar_blogs  = published_posts.order_by("-created_at")[:10]
    popular_blogs  = published_posts.order_by("-views", "-likes")[:5]

    context = {
        "blogs":         blogs,
        "category":      categories,
        "sidebar_blogs": sidebar_blogs,
        "popular_blogs": popular_blogs,
        "action":        "all_article",
    }

    if request.headers.get("HX-Request"):
        return render(request, "components/category/all_article_partial.html", context)
    return render(request, "components/category/all_article.html", context)


def right_blog_details_partial(request, slug):
    blog = get_object_or_404(BlogPost, slug=slug)

    content          = blog.description.split()
    first_50_words   = ' '.join(content[:50])
    remaining_words  = ' '.join(content[50:])
    current_user     = request.user if request.user.is_authenticated else None

    context = {
        'blog':             blog,
        'first_50_words':   first_50_words,
        'remaining_words':  remaining_words,
        'user':             current_user,
        'action':           'right_side_update_in_blog_details',
    }

    if request.headers.get("HX-Request"):
        return render(request, "components/blog_details/blog_right_side_partial.html", context)
    return render(request, "components/blog_details/blog_right_side.html", context)


def update_blog_stat(request, slug, stat_type):
    blog = get_object_or_404(BlogPost, slug=slug)

    if stat_type == "like":
        blog.likes += 1
    elif stat_type == "view":
        blog.views += 1
    elif stat_type == "share":
        blog.shares += 1

    blog.save()

    return HttpResponse(
        blog.likes if stat_type == "like"
        else blog.views if stat_type == "view"
        else blog.shares
    )


@login_required
def create_blog(request):
    categories   = Category.objects.all()
    subcategories = SubCategory.objects.all()
    all_tags = Tag.objects.all().order_by('name')
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                new_blog = form.save(commit=False)
                new_blog.author = request.user
                new_blog.status = "pending"

                category = form.cleaned_data.get("category")
                subcategory = form.cleaned_data.get("subcategory")
                if subcategory and category and subcategory.category_id != category.id:
                    subcategory = None
                new_blog.subcategory = subcategory

                if new_blog.featured_image:
                    new_blog.featured_image_url = None

                new_blog.save(skip_auto_status=True)
                form.save_m2m()

                messages.success(request, "Blog post created successfully!")

                if request.headers.get("HX-Request"):
                    response = HttpResponse(status=204)
                    response["HX-Redirect"] = reverse('homepage')
                    return response

                return redirect(reverse('homepage'))

            except Exception as e:
                print(f"Error: {e}")
                messages.error(request, "An internal error occurred.")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = BlogPostForm()

    context = {
        "categories":   categories,
        "subcategories": subcategories,
        "form":         form,
        "action":       "post_create",
        "is_edit":      False,
        "post":         None,
        "selected_tags": [],
        "all_tags":     all_tags,
    }

    if request.headers.get("HX-Request"):
        return render(request, "components/blogs/partial_create_blog_content.html", context)

    return render(request, "base.html", context)


@login_required
def edit_blog(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, author=request.user)
    categories = Category.objects.all()
    subcategories = SubCategory.objects.all()
    all_tags = Tag.objects.all().order_by('name')

    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            updated_post = form.save(commit=False)
            updated_post.author = request.user

            category = form.cleaned_data.get("category")
            subcategory = form.cleaned_data.get("subcategory")
            if subcategory and category and subcategory.category_id != category.id:
                subcategory = None
            updated_post.subcategory = subcategory

            if updated_post.featured_image:
                updated_post.featured_image_url = None

            updated_post.save(skip_auto_status=True)
            form.save_m2m()

            messages.success(request, "Blog post updated and sent for review.")

            if request.headers.get("HX-Request"):
                response = HttpResponse(status=204)
                response["HX-Redirect"] = reverse('user_dashboard')
                return response

            return redirect('user_dashboard')

        messages.error(request, "Please fix the errors below.")
    else:
        form = BlogPostForm(instance=post)

    selected_tags = [
        {"id": tag.id, "label": tag.name}
        for tag in post.tags.all()
    ]

    context = {
        "categories": categories,
        "subcategories": subcategories,
        "form": form,
        "action": "post_edit",
        "is_edit": True,
        "post": post,
        "selected_tags": selected_tags,
        "all_tags": all_tags,
    }

    if request.headers.get("HX-Request"):
        return render(request, "components/blogs/partial_create_blog_content.html", context)

    return render(request, "base.html", context)


@cache_page(60 * 2)
@vary_on_headers("HX-Request")
def category_post(request, slug):
    category = get_object_or_404(
        Category.objects.prefetch_related('subcategories'),
        slug=slug
    )

    published_posts      = published_posts_queryset()
    blogs                = published_posts.filter(category=category).prefetch_related("shares")

    subcategory_blogs_map = {}
    for subcategory in category.subcategories.all():
        sub_blogs = (
            published_posts
            .filter(subcategory=subcategory)
            .prefetch_related("shares")
        )
        if sub_blogs.exists():
            subcategory_blogs_map[subcategory] = sub_blogs

    sidebar_blogs  = published_posts.order_by("-created_at")[:10]
    popular_blogs  = published_posts.order_by("-views", "-likes")[:5]
    most_viewed = BlogPost.objects.filter(
        status="published"
    ).exclude(
        featured_image=''
    ).order_by('-views').only(
        'title', 'slug', 'featured_image', 'featured_image_url', 'views'
    )[:8]

    context = {
        "category":             category,
        "blogs":                blogs,
        "sidebar_blogs":        sidebar_blogs,
        "popular_blogs":        popular_blogs,
        "most_viewed_blogs":    most_viewed,
        "subcategory_blogs_map": subcategory_blogs_map,
        "action":               "category_post",
    }

    if request.headers.get("HX-Request"):
        return render(request, "components/category/category_post_partial.html", context)
    return render(request, "components/category/category_post.html", context)


def contact_page(request):
    context = {'action': 'contact_page'}
    if request.headers.get("HX-Request"):
        return render(request, "partial_contact_us_page.html", context)
    return render(request, 'contact_us_page.html', context)


@login_required
@require_POST
def add_comment(request, post_slug):
    post    = get_object_or_404(BlogPost, slug=post_slug)
    content = request.POST.get('content', '').strip()

    if not content:
        return redirect('blog_details', slug=post_slug)

    Comment.objects.create(post=post, user=request.user, content=content)
    if request.headers.get("HX-Request"):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = f"/details/{post_slug}/#comments"
        return response
    return redirect('blog_details', slug=post_slug)


@login_required
@require_POST
def add_reply(request, comment_id):
    parent_comment = get_object_or_404(Comment, id=comment_id)
    post_slug      = parent_comment.post.slug
    content        = request.POST.get('content', '').strip()

    if not content:
        return redirect('blog_details', slug=post_slug)

    Reply.objects.create(comment=parent_comment, user=request.user, content=content)
    if request.headers.get("HX-Request"):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = f"/details/{post_slug}/#comments"
        return response
    return redirect('blog_details', slug=post_slug)


@login_required
def user_like_toggle(request, like_slug):
    if request.user.is_verified:
        blog_post = get_object_or_404(BlogPost, slug=like_slug)
        user      = request.user

        try:
            like_instance = Like.objects.get(post=blog_post, user=user)
            like_instance.delete()
        except Like.DoesNotExist:
            try:
                Like.objects.create(post=blog_post, user=user)
            except IntegrityError:
                logout(request)
                return redirect('login')

    if request.headers.get("HX-Request"):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = f"/details/{like_slug}/"
        return response

    return redirect('blog_details', slug=like_slug)


@require_POST
def record_share(request, post_slug):
    platform = request.POST.get('platform')

    try:
        post = get_object_or_404(BlogPost, slug=post_slug)

        if request.user.is_authenticated:
            share_instance, created = Share.objects.get_or_create(
                post=post,
                user=request.user,
                platform=platform,
                defaults={'platform': platform}
            )
            if created:
                return JsonResponse({"status": "success", "message": f"New share recorded on {platform}."})
            return JsonResponse({"status": "info", "message": f"Share already counted for this user on {platform}."})
        else:
            Share.objects.create(post=post, user=None, platform=platform)
            return JsonResponse({"status": "success", "message": f"Share recorded (Anonymous) on {platform}."})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def tag_posts(request, tag_slug):
    tag = get_object_or_404(Tag, slug=tag_slug)
    blogs = published_posts_queryset().filter(tags=tag).order_by("-created_at")
    total_blogs = blogs.count()

    context = {
        'tag': tag,
        'blogs': blogs,
        'total_blogs': total_blogs,
    }
    return render(request, 'components/blogs/tag_realted_post.html', context)


def popular_tags_modal(request):
    all_tags = Tag.objects.annotate(num_posts=Count('blog_posts')).order_by('-num_posts')
    return render(
        request,
        'components/home/partials/popular_tags_modal_content.html',
        {'all_tags': all_tags},
    )