from django.urls import path

from .views import (
    home,
    all_blog_post_view,
    blog_details_view,
    update_blog_stat,
    category_post,
    create_blog,
    contact_page,
    popular_blog_post,
    all_article,

    right_blog_details_partial,
    
    blog_details_view,
    user_like_toggle,
    redirect_search_results,
    record_share
)

from interactions.views import share_post
from .views import add_comment, add_reply

urlpatterns = [
    path("", home, name="homepage"),
    path("blogs/", all_blog_post_view, name="blogs"),
    path("popular-blogs/", popular_blog_post, name="popular_blogs"),
    path("all-blog/", all_article, name='all_article'),
    path("blog_details/<slug:slug>/", blog_details_view, name="blog_details"),
    path('blog/detials/update/<slug:slug>/', right_blog_details_partial, name='right_blog_details_partial'),
    

    path('category/<slug:slug>/', category_post, name='category_post'),
    
    path(
        "update/<slug:slug>/<str:stat_type>/",
        update_blog_stat,
        name="update_blog_stat",
    ),

    path("blogs/create_blog/" , create_blog , name="create_blog"),

    path("contact/", contact_page, name="contact_page" ),

    
    path('share-post/',share_post, name='share_post'),
    
    path('post/<slug:post_slug>/share/', record_share, name='record_share'),    

    
    path('post/<slug:post_slug>/comment/', add_comment, name='add_comment'),

    path('comment/<int:comment_id>/reply/', add_reply, name='add_reply'),
    
    path('like/<slug:like_slug>/', user_like_toggle, name='user_like_toggle'),
    
    path('search/', redirect_search_results, name='redirect_search_results'),
    
 
]



