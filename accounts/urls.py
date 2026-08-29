from django.urls import path
from . import views

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    # path("verify-code/", views.verify_code_view, name="verify-code"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("forget-password/", views.forget_password_view, name="forget-password"),
    path("reset-code/", views.reset_code_view, name="reset-code"),
    path("new-password/", views.new_password_view, name="new-password"),

    path("user_dashboard/" , views.user_dashboard_view , name= "user_dashboard"),
    path("contact_us/" , views.contact_us_view , name= "contact_us"),
    
    path('profile/edit/', views.profile_update_view, name='profile_update'),
    path('check-email/', views.check_email_exists, name='check_email'),
    
    # API Token dashboard page
    path('api-tokens/', views.user_api_tokens_view, name='user_api_tokens'),
    
    # Notifications dashboard page
    path('notifications/', views.user_notifications, name='user_notifications'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('notifications/delete/<int:notif_id>/', views.delete_notification, name='delete_notification'),
]
