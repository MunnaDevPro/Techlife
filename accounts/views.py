# accounts/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from accounts.models import CustomUserModel, EmailVerificationCode
from blog_post.models import BlogPost 
from django.shortcuts import render
from django.db.models import Sum, Count
from django.contrib.auth.decorators import login_required
from blog_post.models import BlogPost
from comments.models import Comment
from earnings.models import EarningSetting  # replace 'your_app_name' with the actual app name where EarningSetting is defined
from django.utils import timezone
from datetime import timedelta
from accounts.utils import send_verification_code_email
from blog_post.models import BlogPost
from accounts.models import CustomUserModel

# views.py - signup_view (CORRECTED)
def signup_view(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if not password:
            messages.error(request, "Password is required.")
            return redirect("signup")
            
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("signup")

        if CustomUserModel.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("signup")

        try:
            user = CustomUserModel.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password, 
                is_active=True,
                is_verified=True,
            )
            messages.success(request, "Account created successfully! Please login.")
            return redirect("login")
            
        except Exception as e:
            messages.error(request, f"Error creating account: {str(e)}")
            return redirect("signup")

    return render(request, "account/register_page.html")
# -------------------- VERIFY EMAIL --------------------
def verify_code_view(request):
    user_id = request.session.get("pending_user_id")
    if not user_id:
        return redirect("signup")

    user = CustomUserModel.objects.get(id=user_id)

    if request.method == "POST":
        code = request.POST.get("code")
        try:
            code_obj = EmailVerificationCode.objects.get(user=user, code=code, is_used=False, purpose="verify")
            user.is_verified = True
            user.is_active = True
            user.save()
            code_obj.is_used = True
            code_obj.save()
            messages.success(request, "Email verified successfully! Please login.")
            # del request.session["pending_user_id"]
            return redirect("login")
        except EmailVerificationCode.DoesNotExist:
            messages.error(request, "Invalid or expired code.")

    return render(request, "account/verify_code.html")


# -------------------- LOGIN --------------------
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)
   
        if user is None:
            messages.error(request, "Invalid email or password.")
            return redirect("login")

        login(request, user)
        messages.success(request, "Logged in successfully.")
        return redirect("homepage")

    return render(request, "account/login_page.html")

def logout_view(request):
    logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect("homepage")


def forget_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = CustomUserModel.objects.get(email=email)
            code_obj = EmailVerificationCode.objects.create(user=user, purpose="reset")
            send_verification_code_email(user, code_obj.code, "reset")
            request.session["reset_user_id"] = user.id
            messages.info(request, "A password reset code has been sent to your email.")
            return redirect("reset-code")
        except CustomUserModel.DoesNotExist:
            messages.error(request, "No account found with this email.")
    return render(request, "account/forget_password.html")


def reset_code_view(request):
    user_id = request.session.get("reset_user_id")
    if not user_id:
        return redirect("forget-password")

    user = CustomUserModel.objects.get(id=user_id)

    if request.method == "POST":
        code = request.POST.get("code")
        try:
            code_obj = EmailVerificationCode.objects.get(user=user, code=code, is_used=False, purpose="reset")
            code_obj.is_used = True
            code_obj.save()
            request.session["allow_new_password"] = user.id
            messages.success(request, "Code verified. Please set your new password.")
            return redirect("new-password")
        except EmailVerificationCode.DoesNotExist:
            messages.error(request, "Invalid or expired code.")

    return render(request, "account/reset_password.html")


def new_password_view(request):
    user_id = request.session.get("allow_new_password")
    if not user_id:
        return redirect("forget-password")

    user = CustomUserModel.objects.get(id=user_id)

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("new-password")

        user.set_password(password)
        user.save()

        del request.session["allow_new_password"]
        messages.success(request, "Password updated successfully. Please login.")
        return redirect("login")

    return render(request, "account/new_password.html")


def contact_us_view(request):
    # Check if it's an HTMX request
    if request.headers.get('HX-Request'):
        # Return only the content without base layout
        return render(request, "contact_us_content.html")
    
    # Return full page with base layout
    return render(request, "contact_us_page.html")




# User dashboard section
@login_required

def user_dashboard_view(request):
    user = request.user
    user_blog_posts = BlogPost.objects.filter(author=user).select_related('author','category').prefetch_related('comments').order_by('-created_at')
    

    total_reaction = BlogPost.objects.filter(author=request.user).annotate(
    like_count=Count('likes')
    ).aggregate(total_likes=Sum('like_count'))['total_likes'] or 0
    
    total_views = user_blog_posts.aggregate(total=Sum('views'))['total'] or 0
    total_quality = user_blog_posts.aggregate(total=Sum('content_quality'))['total'] or 0
    
    
    last_week_start = timezone.now() - timedelta(days=7)
    views_last_week = total_views / 4
    
    
    last_month_start = timezone.now() - timedelta(days=30) 
    views_last_month = int(total_views / 3)
    
    
    latest_comment = (
        Comment.objects
        .filter(post__author=user) 
        .order_by('-created_at')   
        .select_related('post')    
        .first()         
    )
    

    comment_count = Comment.objects.filter(post__author=user).count()
    reply_count = Comment.objects.filter(post__author=user).annotate(
        num_replies=Count('replies')
    ).aggregate(total_replies=Sum('num_replies'))['total_replies'] or 0
    total_comments = comment_count + reply_count




    # earning section logic
    # earning = EarningSetting.objects.first()  

    # post_point = earning.quality_rate * total_quality

    # others_point = (
    #     total_views * earning.view_rate +
    #     total_reaction * earning.like_rate +
    #     total_comments * earning.comment_rate
    # )

    # total_point = post_point + others_point


    # badge section
    # badge_level  = ""
    # if (1<total_point<=50):
    #     badge_level +="Bronze"
    # elif (50<total_point<=80):
    #     badge_level +="Silver"
    # elif (80<total_point<=120):
    #     badge_level +="Gold"
    # elif (120<total_point<=150):
    #     badge_level +="Platinum"
    # elif (150<total_point<=200):
    #     badge_level +="Diamond"
    # elif (200<total_point<=250):
    #     badge_level +="Master"
    # elif (250<total_point<=300):
    #     badge_level +="Legend"
    # elif total_point > 300:
    #     badge_level  += "Grand Master"   


    context = {
        "user": user,
        "user_blog_posts": user_blog_posts,
        "total_views": total_views,
        "total_comments": total_comments,
        "total_reaction" : total_reaction,
        # "others_point" : others_point,
        # "post_point" : post_point,
        # "total_point" : total_point,
        # "badge_level" : badge_level,
        "views_last_week": int(views_last_week),
        "latest_comment":latest_comment,
        "views_last_month":views_last_month,
        "action":"user_dashboard"
       
    }

    # return render(request, "account/user_dashboard.html", context)
    return render(request, "account/demo/user_dashboard.html", context)


# def particular_user_view(request, id):
  
#     user_to_show = get_object_or_404(CustomUserModel, id=id)

#     user_posts = BlogPost.objects.filter(author=user_to_show)
    

#     context = {
#         'user_to_show': user_to_show,
#         'user_posts': user_posts,
#         'total_posts': user_posts.count(),
#     }
    
#     return render(request, 'account/particular_user_profile.html', context)



@login_required
def profile_update_view(request):
    user = request.user
    
    if request.method == 'POST':

        profile_picture_file = request.FILES.get('profile_picture') 
        
 
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.address_line_1 = request.POST.get('address_line_1', user.address_line_1)
        user.address_line_2 = request.POST.get('address_line_2', user.address_line_2)
        user.city = request.POST.get('city', user.city)
        user.postcode = request.POST.get('postcode', user.postcode)
        user.country = request.POST.get('country', user.country)
        user.mobile = request.POST.get('mobile', user.mobile)
        
        if profile_picture_file:
            user.profile_picture = profile_picture_file
    
            
        
        user.save()
        # messages.success(request, 'Your profile has been updated successfully!')
        return redirect('user_dashboard') 

    context = {
        'user_data': user, 
        "action": "profile_update"
    }
    
    return render(request, 'account/demo/profile_update.html', context)