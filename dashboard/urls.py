from django.urls import path
from django.contrib.auth import views as auth_views
from dashboard.views import views
from dashboard.views.overview import overview
from dashboard.views import content
from dashboard.views import moderation
from dashboard.views import forum
from dashboard.views import users
from dashboard.views import seo
from dashboard.views import analytics
from dashboard.views import site_config

app_name = "dashboard"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="dashboard/login.html"), name="login"),
    path("", overview, name="overview"),
    
    # Content
    path("content/posts/", content.post_list, name="content_posts"),
    path("content/posts/<int:pk>/approve/", content.post_approve, name="post_approve"),
    path("content/posts/<int:pk>/reject/", content.post_reject, name="post_reject"),
    path("content/posts/<int:pk>/delete/", content.post_delete, name="post_delete"),
    path("content/posts/bulk/", content.post_bulk_action, name="post_bulk"),
    path("content/posts/<int:pk>/status/", content.post_update_status, name="post_status_update"),
    path("content/posts/create/", content.post_create, name="post_create"),
    path("content/posts/<int:pk>/edit/", content.post_detail_edit, name="post_edit"),
    path("content/posts/<int:post_pk>/comments/<int:comment_pk>/delete/", content.post_comment_delete, name="post_comment_delete"),
    
    path("content/pending/", content.post_list, name="content_pending"),
    path("content/subcategories/", content.subcategory_list_crud, name="content_subcategories"),
    path("content/categories/", content.category_list_crud, name="content_categories"),
    path("content/tags/", content.tag_list_crud, name="content_tags"),
    path("content/homepage/", content.homepage_sections, name="content_homepage"),
    path("content/homepage/sections/", content.homepage_sections, name="content_homepage_sections"),
    
    # Forum
    path("forum/questions/", forum.question_list, name="forum_questions"),
    path("forum/questions/<int:pk>/edit/", forum.question_edit, name="forum_question_edit"),
    path("forum/questions/<int:pk>/delete/", forum.question_delete, name="question_delete"),
    path("forum/answers/", forum.answer_list, name="forum_answers"),
    path("forum/answers/<int:pk>/delete/", forum.answer_delete, name="answer_delete"),
    path("forum/reported/", moderation.forum_queue, name="forum_reported"),
    
    # Moderation
    path("mod/flagged/", moderation.moderation_queue, name="mod_flagged"),
    path("mod/comments/", moderation.comment_queue, name="mod_comments"),
    path("mod/blocked/", moderation.blocked_users, name="mod_blocked"),
    path("mod/users/<int:pk>/unblock/", moderation.user_unblock, name="user_unblock"),
    
    # Flags Actions
    path("mod/flags/<int:pk>/approve/<str:queue_type>/", moderation.flag_approve, name="flag_approve"),
    path("mod/flags/<int:pk>/remove/<str:queue_type>/", moderation.flag_remove, name="flag_remove"),
    path("mod/flags/<int:pk>/skip/<str:queue_type>/", moderation.flag_skip, name="flag_skip"),
    path("mod/flags/reset/<str:queue_type>/", moderation.reset_skip_list, name="reset_skip_list"),
    
    # Users
    path("users/all/", users.user_list, name="users_all"),
    path("users/<int:pk>/", users.user_detail, name="user_detail"),
    path("users/<int:pk>/delete/", users.user_delete, name="user_delete"),
    path("users/verification/", users.verification_requests, name="users_verification"),
    path("users/<int:pk>/verify/", users.manual_verify_user, name="user_verify"),
    path("users/roles/", users.roles_permissions, name="users_roles"),
    
    # SEO
    path("seo/audit/", seo.meta_audit, name="seo_audit"),
    path("seo/sitemap/", seo.sitemap_status, name="seo_sitemap"),
    path("seo/broken/", seo.broken_links, name="seo_broken"),
    
    # Analytics
    path("analytics/traffic/", analytics.traffic_overview, name="analytics_traffic"),
    path("analytics/posts/", analytics.top_posts, name="analytics_posts"),
    path("analytics/authors/", analytics.author_performance, name="analytics_authors"),
    
    # Settings
    path("settings/ads/", site_config.ads_config, name="settings_ads"),
    path("settings/footer/", site_config.footer_logo_config, name="settings_footer"),
    path("settings/maintenance/", site_config.maintenance_config, name="settings_maintenance"),
    
    # Notifications
    path("notifications/", views.notifications, name="notifications"),
]
