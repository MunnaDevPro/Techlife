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
    
    # path('profile/<int:id>/', views.particular_user_view, name='particular_user_view'),
    
]
