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
    path("user-dashboard/company/<int:pk>/edit/", views.user_company_edit_view, name="user_company_edit"),
    path("contact_us/" , views.contact_us_view , name= "contact_us"),
    
    path("manage-company/<int:company_id>/", views.manage_company_view, name="manage_company"),
    path("manage-company/<int:company_id>/delete/<str:item_type>/<int:item_id>/", views.delete_company_item_view, name="delete_company_item"),
    
    path('profile/edit/', views.profile_update_view, name='profile_update'),
    path('check-email/', views.check_email_exists, name='check_email'),
    path('api/traffic-data/', views.user_traffic_api, name='user_traffic_api'),
    
    # API Token dashboard page
    path('api-tokens/', views.user_api_tokens_view, name='user_api_tokens'),
    
    # Notifications dashboard page
    path('notifications/', views.user_notifications, name='user_notifications'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('notifications/delete/<int:notif_id>/', views.delete_notification, name='delete_notification'),
    path('notifications/bulk-delete/', views.bulk_delete_notifications, name='bulk_delete_notifications'),
]
