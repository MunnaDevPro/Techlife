from django.urls import path

from .views import (
    home,
    all_blog_post_view,
    blog_details_view,
    update_blog_stat,
    category_post,
    create_blog,
    edit_blog,
    contact_page,
    popular_blog_post,
    all_article,

    right_blog_details_partial,
    
    blog_details_view,
    user_like_toggle,
    redirect_search_results,
    record_share,
    tag_posts,
    popular_tags_modal,
)

from interactions.views import share_post
from .views import add_comment, add_reply

urlpatterns = [
    path("", home, name="homepage"),
    path("blogs/", all_blog_post_view, name="blogs"),
    path("popular-blogs/", popular_blog_post, name="popular_blogs"),
    path("all-blog/", all_article, name='all_article'),
    path("details/<slug:slug>/", blog_details_view, name="blog_details"),
    path("company/<slug:slug>/", blog_details_view, name="company_details"),
    path('blog/detials/update/<slug:slug>/', right_blog_details_partial, name='right_blog_details_partial'),
    

    path('category/<slug:slug>/', category_post, name='category_post'),
    
    path(
        "update/<slug:slug>/<str:stat_type>/",
        update_blog_stat,
        name="update_blog_stat",
    ),

    path("blogs/create_blog/" , create_blog , name="create_blog"),
    path("blogs/<slug:slug>/edit/", edit_blog, name="edit_blog"),

    path("contact/", contact_page, name="contact_page" ),

    
    path('share-post/',share_post, name='share_post'),
    
    path('post/<slug:post_slug>/share/', record_share, name='record_share'),    

    
    path('post/<slug:post_slug>/comment/', add_comment, name='add_comment'),

    path('comment/<int:comment_id>/reply/', add_reply, name='add_reply'),
    
    path('like/<slug:like_slug>/', user_like_toggle, name='user_like_toggle'),
    
    path('search/', redirect_search_results, name='redirect_search_results'),

    path('tag/<slug:tag_slug>/', tag_posts, name='tag_posts'),
    path('popular-tags/modal/', popular_tags_modal, name='popular_tags_modal'),

    # Review Flow
    path('write-review/', __import__('blog_post.views').views.write_review_landing, name='write_review_landing'),
    path('write-review/<int:post_id>/step-1/', __import__('blog_post.views').views.write_review_step1, name='write_review_step1'),
    path('write-review/<int:post_id>/step-2/', __import__('blog_post.views').views.write_review_step2, name='write_review_step2'),
    path('write-review/<int:post_id>/step-3/', __import__('blog_post.views').views.write_review_step3, name='write_review_step3'),
    path('write-review/<int:post_id>/success/', __import__('blog_post.views').views.write_review_success, name='write_review_success'),

    # Add Company Flow
    path('add-company/', __import__('blog_post.views').views.add_company_step1, name='add_company_step1'),
    path('add-company/step-2/', __import__('blog_post.views').views.add_company_step2, name='add_company_step2'),
    path('add-company/step-3/', __import__('blog_post.views').views.add_company_step3, name='add_company_step3'),
    path('add-company/success/', __import__('blog_post.views').views.add_company_success, name='add_company_success'),
]



