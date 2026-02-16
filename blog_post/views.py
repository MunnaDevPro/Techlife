from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.db.models import Count
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from .models import BlogPost, Category, Review, SubCategory
from .models import BlogPost, BlogAdditionalImage, Category, Tag
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


from interactions.models import Share
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from blog_post.models import Post_view_ip


# Ip Tracking system for views section
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')



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


    
    
    most_viewed_blogs = BlogPost.objects.filter(status="published").order_by("-views")


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
        
        
    
    # user like system check
    user_has_liked = False
    if request.user.is_authenticated:
        try:
            Like.objects.get(post=blog_detail, user=request.user)
            user_has_liked = True
        except Like.DoesNotExist:
            user_has_liked = False
            
            
    #  ip checking for views section count
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
        "blog_detail": blog_detail,
        "related_news":related_news,
        "word_count":word_count,
        "most_viewed_blogs":most_viewed_blogs,
        "all_comments" : page_obj,
        "total_comments":total_comments,
        "user_has_liked":user_has_liked,
        "sort_by":sort_by,
        "action":"blog_details",
    }
    
    if request.headers.get("HX-Request"):
        return render(request, "components/blog_details/partial_blog_details_page.html", context)
    return render(request, "components/blog_details/blog_details_page.html", context)




def home(request):
   
    blogs = BlogPost.objects.filter(status="published")[:6]

    top_categories = Category.objects.annotate(
        post_count=Count('blogpost') 
    ).filter(post_count__gt=0).order_by('-post_count')[:3]

    first_category = top_categories[0] if top_categories.count() > 0 else None
    second_category = top_categories[1] if top_categories.count() > 1 else None
    third_category = top_categories[2] if top_categories.count() > 2 else None

    first_blogs = BlogPost.objects.filter(category=first_category, status='published').order_by('-created_at')
    second_blogs = BlogPost.objects.filter(category=second_category, status='published').order_by('-created_at')
    third_blogs = BlogPost.objects.filter(category=third_category, status='published').order_by('-created_at')



    latest_blog = (
        BlogPost.objects.filter(status="published").order_by("-created_at").first()
    )
    
    all_category = Category.objects.all()

    # top 5 published blogs for carousel
    carousel_blogs = BlogPost.objects.filter(status="published").order_by(
        "-created_at"
    )[:5]

    top_users = CustomUserModel.objects.filter(is_verified=True) \
    .annotate(post_count=Count('authored_posts')) \
    .order_by('-post_count')[:4]

    # category wise 4 ta kore blogs nibo
    tech_cat = Category.objects.filter(slug='technology').first()

    technology_posts = BlogPost.objects.filter(
        status="published", 
        category__slug='technology'
    ).order_by("-created_at")[:4]


    news_cat = Category.objects.filter(slug='news').first()
    news_posts = BlogPost.objects.filter(
        status="published", 
        category__slug='news'
    ).order_by("-created_at")[:4]
    

    tips_cat = Category.objects.filter(slug='tips-tricks').first()
    tips_posts = BlogPost.objects.filter(
        status="published", 
        category__slug='tips-tricks'
    ).order_by("-created_at")[:4]

    # only latest blogs 
    Only_latest_blogs = (
        BlogPost.objects.filter(status="published")
        .select_related("category", "author")
        .order_by("-created_at")[:1]
    ) 
    
    # latest and popular blogs
    latest_popular_blogs = (
        BlogPost.objects.filter(status="published")
        .select_related("category", "author")
        .order_by("-created_at", "-views", "-likes")[:8]
    ) 
    
    
    
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

    # latest category 
    popular_posts_flat_list = []

    for category in popular_categories:
       
        latest_post = (
            BlogPost.objects
            .filter(category=category, status='published')
            .order_by('-created_at')[:1] 
        )
        
        if latest_post:
            post = latest_post[0]
            
            # Add the post in flat list
            popular_posts_flat_list.append({
                'title': post.title,
                'created_at':post.created_at,
                'slug': post.slug,
                'views': post.views,
                'author_username': post.author.username,
                'category_name': category.name, 
                'category_icon': category.font_awesome_icon, 
                'featured_image': post.featured_image,
                'featured_image_url': post.featured_image_url,
            })

        
    
    # news related post
    news__related_posts = BlogPost.objects.filter(
        status="published", 
        category__slug='news'
    ).order_by("-views","-likes","-created_at")
    
    # technology related post
    Teacnology_related_posts = BlogPost.objects.filter(
        status="published", 
        category__slug='technology'
    ).order_by("-views","-likes","-created_at")

    # programming related post
    programming_related_posts = BlogPost.objects.filter(
        status="published", 
        category__slug='programming'
    ).order_by("-views","-likes","-created_at")



    # Most viewed
    most_viewed_blogs = BlogPost.objects.filter(status="published").order_by("-views")


    #company logo
    logos = compnay_logo.objects.all()


    all_tags = Tag.objects.annotate(
        num_posts=Count('blog_posts')
    ).order_by('-num_posts')

    top_tags = all_tags[:15]



    context = {
        "first_category" : first_category,
        "second_category": second_category,
        "third_category" : third_category,

        "tech_cat" : tech_cat,
        "news_cat" : news_cat,
        "tips_cat": tips_cat,

        "first_blogs":first_blogs,
        "second_blogs":second_blogs,
        "third_blogs":third_blogs,

        "blogs": blogs,
        "latest_blog": latest_blog,
        "top_users": top_users,
        "carousel_blogs": carousel_blogs,
        "top_tags": top_tags,
        "technology_posts":technology_posts,
        "news_posts":news_posts,
        "tips_posts":tips_posts,
        "Only_latest_blogs":Only_latest_blogs,
        "latest_popular_blogs": latest_popular_blogs,
        "popular_posts_flat_list": popular_posts_flat_list,
        "news__related_posts":news__related_posts,
        "Teacnology_related_posts":Teacnology_related_posts,
        "programming_related_posts":programming_related_posts,
        "most_viewed_blogs":most_viewed_blogs,
        "all_category":all_category,
        "logos":logos,

        "top_categories":top_categories,
        
        
        "action" : "home_page",
    }

    if request.headers.get("HX-Request"):
        return render(request, "components/home/partial_homepage.html", context)

    return render(request, "home.html", context)



def redirect_search_results(request):

    query = request.GET.get('q', '').strip()
    
    if not query:
        return redirect('homepage') 

    try:
        category_match = Category.objects.get(name__iexact=query)
        return redirect('category_post', slug=category_match.slug)
    except Category.DoesNotExist:
        pass
    
    # Search SubCategory Match 
    try:
        subcategory_match = SubCategory.objects.select_related('category').get(name__iexact=query)
        return redirect('category_post', slug=subcategory_match.category.slug)
    except SubCategory.DoesNotExist:
        pass
        

    blog_post_match = BlogPost.objects.select_related('category').filter(
        Q(title__icontains=query) | Q(subtitle__icontains=query), 
        status="published"
    ).first()

    if blog_post_match and blog_post_match.category:
        return redirect('category_post', slug=blog_post_match.category.slug)
            
    return redirect('homepage')



def all_blog_post_view(request):

    blogs = BlogPost.objects.filter(status="published").select_related(
        "category", "author"
    ).order_by('-created_at')
    categories = Category.objects.all()
    

    # Sidebar content
    sidebar_blogs = (
        BlogPost.objects.filter(status="published")
        .select_related("category", "author")
        .order_by("-created_at")[:10]
    )
    popular_blogs = (
        BlogPost.objects.filter(status="published")
        .select_related("category", "author")
        .order_by("-views", "-likes")[:5]
    )
    
    paginator = Paginator(blogs, 8)  
    
    page_number = request.GET.get('page')

    blogs = paginator.get_page(page_number)
    

    

    context = {
        "blogs": blogs,
        "categories": categories,
        "sidebar_blogs": sidebar_blogs,
        "popular_blogs": popular_blogs,
        'action':'all_blogs',
    }


    # if request.headers.get("HX-Request"):
    #     return render(request, "components/blogs/partial_all_blog_page.html", context)
    return render(request, "components/blogs/all_blog_page.html", context)



def popular_blog_post(request):
    popular_blogs_list = (
        BlogPost.objects.filter(
            status="published",
            views__gte=10,
            likes__gte=10
        )
        .select_related("category", "author")
        .order_by( "-id") 
        .distinct()
        
    )
    blogs_per_page = 8 
    
    paginator = Paginator(popular_blogs_list, blogs_per_page)
    
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

    return render(request, "components/popular/popular_post.html", context)

def all_article(request):
    blogs = BlogPost.objects.filter(status="published").select_related(
        "category", "author"
    )
    categories = Category.objects.all()
    

    # Sidebar content
    sidebar_blogs = (
        BlogPost.objects.filter(status="published")
        .select_related("category", "author")
        .order_by("-created_at")[:10]
    )
    popular_blogs = (
        BlogPost.objects.filter(status="published")
        .select_related("category", "author")
        .order_by("-views", "-likes")[:5]
    )

    context = {
        "blogs": blogs,
        "category": categories,
        "sidebar_blogs": sidebar_blogs,
        "popular_blogs": popular_blogs,
        'action':'all_article',
    }


    if request.headers.get("HX-Request"):
        return render(request, "components/category/all_article_partial.html", context)
    return render(request, "components/category/all_article.html", context)



def right_blog_details_partial(request, slug):

    blog = get_object_or_404(BlogPost, slug=slug)
    

    content = blog.description.split()
    first_50_words = ' '.join(content[:50])
    remaining_words = ' '.join(content[50:])

    current_user = request.user if request.user.is_authenticated else None
    
    context = {
        'blog': blog,
        'first_50_words': first_50_words,
        'remaining_words': remaining_words,
        'user': current_user,
        'action' : 'right_side_update_in_blog_details'
      
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
        blog.likes
        if stat_type == "like"
        else blog.views if stat_type == "view" else blog.shares
    )




def create_blog(request):
    categories = Category.objects.all()
    subcategories = SubCategory.objects.all()
    context = {
        "categories": categories,
        "subcategories": subcategories,
    }

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        subcategory_id = request.POST.get('subcategory')
        
        # Images
        featured_image_file = request.FILES.get('featured_image')
        featured_image_url = request.POST.get('featured_image_url')
        tags_list_input = request.POST.get('tags_list')

        if not (title and description and category_id):
            messages.error(request, "Please fill in all required fields.")
            return render(request, "components/blogs/partial_create_blog_content.html", context)

        try:
            category = get_object_or_404(Category, pk=category_id)
            subcategory = None
            if subcategory_id: 
                subcategory = SubCategory.objects.filter(pk=subcategory_id, category=category).first()

            new_blog = BlogPost.objects.create(
                author=request.user,
                category=category,
                subcategory=subcategory,
                title=title,
                description=description,
                featured_image=featured_image_file if featured_image_file else None,
                featured_image_url=featured_image_url if not featured_image_file else None
            )

            if tags_list_input:
                tag_names = [tag.strip().lower() for tag in tags_list_input.split(',') if tag.strip()]
                tag_objects = [Tag.objects.get_or_create(name=name)[0] for name in tag_names]
                new_blog.tags.set(tag_objects)

            messages.success(request, "Blog post created successfully!")

            if request.headers.get("HX-Request"):
                response = HttpResponse(status=204)
                response["HX-Redirect"] = reverse('homepage') 
                return response
            
            return redirect(reverse('homepage'))

        except Exception as e:
            print(f"Error: {e}") 
            messages.error(request, "An internal error occurred.")
            return render(request, "components/blogs/partial_create_blog_content.html", context)

    if request.headers.get("HX-Request"):
        return render(request, "components/blogs/partial_create_blog_content.html", context)

    return render(request, "base.html", context)



# Blog filter by category
def category_post(request, slug):
    
    category = get_object_or_404(
        Category.objects.prefetch_related('subcategories'),
        slug=slug
    )

    blogs = (
        BlogPost.objects.filter(category=category, status="published")
        .select_related("category")
        .prefetch_related("shares")
    )
    
    subcategory_blogs_map = {}
    
    for subcategory in category.subcategories.all():
        sub_blogs = (
            BlogPost.objects.filter(subcategory=subcategory, status="published")
            .select_related("category", "subcategory")
            .prefetch_related("shares")
        )
        if sub_blogs.exists():
            subcategory_blogs_map[subcategory] = sub_blogs

    sidebar_blogs = (
        BlogPost.objects.filter(status="published")
        .select_related("category", "author")
        .order_by("-created_at")[:10]
    )
    popular_blogs = (
        BlogPost.objects.filter(status="published")
        .select_related("category", "author")
        .order_by("-views", "-likes")[:5]
    )

    context = {
        "category": category,
        "blogs": blogs,
        "sidebar_blogs": sidebar_blogs,
        "popular_blogs": popular_blogs,
        "subcategory_blogs_map": subcategory_blogs_map,
        "action" : 'category_post',
    }


    if request.headers.get("HX-Request"):
        return render(request, "components/category/category_post_partial.html", context)

    return render(request, "components/category/category_post.html", context)



def contact_page(request):
    context = {
        'action':'contact_page'
    }
    if request.headers.get("HX-Request"):
        return render(request, "partial_contact_us_page.html", context)
    return render(request, 'contact_us_page.html',context)





@login_required
@require_POST 
def add_comment(request, post_slug):

    post = get_object_or_404(BlogPost, slug=post_slug)
    

    content = request.POST.get('content', '').strip()

    if not content:
        return redirect('post_detail', slug=post_slug)


    Comment.objects.create(
        post=post,
        user=request.user, 
        content=content
    )
    
    
    
    return redirect('blog_details', slug=post_slug)



@login_required
@require_POST
def add_reply(request, comment_id):

    parent_comment = get_object_or_404(Comment, id=comment_id)
    post_slug = parent_comment.post.slug 
    
    
    content = request.POST.get('content', '').strip()

    if not content:
     
        return redirect('post_detail', slug=post_slug)


    Reply.objects.create(
        comment=parent_comment,
        user=request.user, 
        content=content
    )

    return redirect('blog_details', slug=post_slug)



@login_required
def user_like_toggle(request, like_slug):
    
    if request.user.is_verified:

        blog_post = get_object_or_404(BlogPost, slug=like_slug)
        user = request.user
        
        if request.headers.get("HX-Request"):
        
            try:
                like_instance = Like.objects.get(post=blog_post, user=user)
                like_instance.delete()
                
            except Like.DoesNotExist:
                try:
                    Like.objects.create(post=blog_post, user=user)
                
                except IntegrityError:
                
                    logout(request)
                    return redirect('login')
        
    return redirect('blog_details', slug=like_slug)




@require_POST
def record_share(request, post_slug):

    platform = request.POST.get('platform')


    try:
        post = get_object_or_404(BlogPost, slug=post_slug)
        
        if request.user.is_authenticated:
            # Share already exists if created is False
            share_instance, created = Share.objects.get_or_create(
                post=post,
                user=request.user,
                platform=platform,
                defaults={'platform': platform} 
            )

            if created:
                return JsonResponse({"status": "success", "message": f"New share recorded on {platform}."})
            else:
                return JsonResponse({"status": "info", "message": f"Share already counted for this user on {platform}."})

        else:

            Share.objects.create(
                post=post,
                user=None, 
                platform=platform
            )
            return JsonResponse({"status": "success", "message": f"Share recorded (Anonymous) on {platform}."})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    


def tag_posts(request, tag_slug):
    tag = get_object_or_404(Tag, slug=tag_slug)

    blogs = BlogPost.objects.filter(tags=tag, status='published').order_by('-created_at')


    paginator = Paginator(blogs, 8) 
    page = request.GET.get('page')
    
    try:
        blogs = paginator.page(page)
    except PageNotAnInteger:
        blogs = paginator.page(1)
    except EmptyPage:
        blogs = paginator.page(paginator.num_pages)

    
    context = {
        'tag': tag,
        'blogs': blogs,
    }
    return render(request, 'components/blogs/tag_realted_post.html', context)




