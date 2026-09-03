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
from forum.models import Question, Answer
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
import json
from django.urls import reverse
from blog_post.models import BlogPost, CompanyService, CompanyIndustryFocus, CompanyClientFocus, CompanyLocation, CompanyClient, Category, SubCategory
from blog_post.forms import CompanyProfileForm

def check_email_exists(request):
    email = request.GET.get('email', None)
    data = {
        'is_taken': CustomUserModel.objects.filter(email__iexact=email).exists()
    }
    return JsonResponse(data)

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
    if request.headers.get('HX-Request'):
        return render(request, "contact_us_content.html")
    
    return render(request, "contact_us_page.html")




@login_required

def user_dashboard_view(request):
    user = request.user
    section = request.GET.get('section', 'overview')
    
    user_blog_posts = BlogPost.objects.filter(author=user, is_company=False).select_related('author','category').prefetch_related('comments').order_by('-created_at')
    user_companies = BlogPost.objects.filter(author=user, is_company=True).select_related('author','category').prefetch_related('comments').order_by('-created_at')
    all_user_posts = BlogPost.objects.filter(author=user)
    
    # forum section
    user_questions = Question.objects.filter(author=user).prefetch_related('answers').order_by('-created_at')
    user_answers = Answer.objects.filter(author=user).select_related('question').order_by('-created_at')
    questions_count = user_questions.count()
    answers_count = user_answers.count()

    
    user_profile = user
    last_follower = user.followers.all().order_by('-id').first()


    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_answers_7_days = Answer.objects.filter(
    author=user, 
    created_at__gte=seven_days_ago
        ).count()


    total_reaction = all_user_posts.annotate(
        like_count=Count('likes')
        ).aggregate(total_likes=Sum('like_count'))['total_likes'] or 0
        
    total_views = all_user_posts.aggregate(total=Sum('views'))['total'] or 0
    total_quality = all_user_posts.aggregate(total=Sum('content_quality'))['total'] or 0
    
    
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

    # Mark notifications as read if visiting the notifications section
    if section == 'notifications':
        user.notifications.filter(is_read=False).update(is_read=True)
        notifications = user.notifications.all().order_by('-created_at')
    else:
        notifications = None

    company = None
    form = None
    categories = None
    subcategories = None
    services_json = "[]"
    industries_json = "[]"
    client_focuses_json = "[]"
    locations_json = "[]"
    clients_json = "[]"
    form_action_url = ""

    if section == 'edit-company':
        company_id = request.GET.get('company_id') or request.POST.get('company_id')
        if company_id:
            company = get_object_or_404(BlogPost, pk=company_id, author=user, is_company=True)
            form_action_url = f"{reverse('user_dashboard')}?section=edit-company&company_id={company.id}"
            
            if request.method == 'POST':
                form = CompanyProfileForm(request.POST, request.FILES, instance=company)
                if form.is_valid():
                    company = form.save(commit=False)
                    company.is_company = True
                    company.save()
                    form.save_m2m()
                    
                    try:
                        # Services
                        services_data = json.loads(request.POST.get('company_services', '[]'))
                        company.company_services.all().delete()
                        for s in services_data:
                            if s.get('name'):
                                CompanyService.objects.create(company=company, name=s.get('name'), percentage=int(s.get('percentage') or 0))
                        
                        # Industries
                        industries_data = json.loads(request.POST.get('company_industries', '[]'))
                        company.company_industry_focuses.all().delete()
                        for s in industries_data:
                            if s.get('name'):
                                CompanyIndustryFocus.objects.create(company=company, name=s.get('name'), percentage=int(s.get('percentage') or 0))
                        
                        # Client Focus
                        clients_focus_data = json.loads(request.POST.get('company_client_focuses', '[]'))
                        company.company_client_focuses.all().delete()
                        for s in clients_focus_data:
                            if s.get('name'):
                                CompanyClientFocus.objects.create(company=company, name=s.get('name'), percentage=int(s.get('percentage') or 0))
                        
                        # Locations
                        locations_data = json.loads(request.POST.get('company_locations', '[]'))
                        company.company_locations.all().delete()
                        for s in locations_data:
                            if s.get('name'):
                                CompanyLocation.objects.create(company=company, name=s.get('name'))
                        
                        # Clients
                        clients_data = json.loads(request.POST.get('company_clients', '[]'))
                        company.company_clients.all().delete()
                        for s in clients_data:
                            if s.get('name'):
                                CompanyClient.objects.create(company=company, name=s.get('name'))
                    except Exception:
                        pass
                        
                    messages.success(request, f"Successfully updated company '{company.title}'!")
                    return redirect(reverse('user_dashboard') + '?section=companies')
                else:
                    messages.error(request, "Failed to update company. Please check errors in the form.")
            else:
                form = CompanyProfileForm(instance=company)

            categories = Category.objects.filter(is_company_category=True).order_by('name')
            subcategories = SubCategory.objects.select_related('category').all()
            
            services = list(company.company_services.values('name', 'percentage'))
            industries = list(company.company_industry_focuses.values('name', 'percentage'))
            client_focuses = list(company.company_client_focuses.values('name', 'percentage'))
            locations = list(company.company_locations.values('name'))
            clients = list(company.company_clients.values('name'))

            services_json = json.dumps(services if services else [{"name": "", "percentage": ""}])
            industries_json = json.dumps(industries if industries else [{"name": "", "percentage": ""}])
            client_focuses_json = json.dumps(client_focuses if client_focuses else [{"name": "", "percentage": ""}])
            locations_json = json.dumps(locations if locations else [{"name": ""}])
            clients_json = json.dumps(clients if clients else [{"name": ""}])

    context = {
        "user": user,
        "user_blog_posts": user_blog_posts,
        "user_companies": user_companies,
        "total_views": total_views,
        "total_comments": total_comments,
        "total_reaction" : total_reaction,
      
        "views_last_week": int(views_last_week),
        "latest_comment":latest_comment,
        "views_last_month":views_last_month,
        "action":"user_dashboard",


        'user_questions': user_questions,
        'user_answers': user_answers,
        'questions_count': questions_count,
        'answers_count': answers_count,

        'recent_7_days': recent_answers_7_days,
        'last_follower':last_follower,
        'section': section,
        'notifications': notifications,

        "form": form,
        "post": company,
        "company": company,
        "categories": categories,
        "subcategories": subcategories,
        "services_json": services_json,
        "industries_json": industries_json,
        "client_focuses_json": client_focuses_json,
        "locations_json": locations_json,
        "clients_json": clients_json,
        "is_edit_mode": True,
        "form_action_url": form_action_url,
        "cancel_url": reverse('user_dashboard') + '?section=companies',
    }

    return render(request, "account/demo/user_dashboard.html", context)



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
        return redirect('/account/user_dashboard/?section=edit-profile') 

    context = {
        'user_data': user, 
        "action": "profile_update"
    }
    
    return render(request, 'account/demo/profile_update.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# User API Tokens Dashboard View
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def user_api_tokens_view(request):
    """
    Dashboard page for managing personal API tokens.

    GET:  Renders the token list, recent activity log, and usage docs.
    POST (action=generate): Creates a new token and flashes the raw value
         exactly once via request.session so it is shown after redirect.
    POST (action=revoke):   Revokes the specified token (CSRF-protected).
    """
    from accounts.models import UserAPIToken
    from blog_post.models import AutomationPublishLog

    user = request.user

    if request.method == 'POST':
        action = request.POST.get('action')

        # ---- Generate new token ----
        if action == 'generate':
            name = request.POST.get('name', '').strip()[:100]
            token_obj, raw_token = UserAPIToken.generate(user=user, name=name)
            # Flash raw token once via session — never persisted in DB
            request.session['_new_api_token'] = {
                'id': token_obj.pk,
                'name': token_obj.name or 'Unnamed',
                'prefix': token_obj.token_prefix,
                'raw_token': raw_token,
            }
            messages.success(
                request,
                'New API token generated! Copy it now — it will not be shown again.'
            )
            return redirect('user_api_tokens')

        # ---- Revoke a token ----
        if action == 'revoke':
            token_id = request.POST.get('token_id')
            try:
                token_obj = UserAPIToken.objects.get(pk=token_id, user=user)
                token_obj.revoke()
                messages.success(request, f'Token "{token_obj.name or token_obj.token_prefix}..." has been revoked.')
            except UserAPIToken.DoesNotExist:
                messages.error(request, 'Token not found.')
            return redirect('user_api_tokens')

    # ---- GET ----
    # Pop the one-time raw token from session if present
    new_token_data = request.session.pop('_new_api_token', None)

    tokens = UserAPIToken.objects.filter(user=user).order_by('-created_at')

    recent_logs = AutomationPublishLog.objects.filter(
        token_user=user,
        auth_source='user_token',
    ).order_by('-created_at')[:20]

    context = {
        'user': user,
        'tokens': tokens,
        'recent_logs': recent_logs,
        'new_token_data': new_token_data,   # None unless just generated
        'action': 'api_tokens',
    }
    return render(request, 'account/demo/api_tokens.html', context)

# ─────────────────────────────────────────────────────────────────────────────
# Notification Views
# ─────────────────────────────────────────────────────────────────────────────

from django.http import HttpResponse, JsonResponse

@login_required
def user_notifications(request):
    notifications = request.user.notifications.all().order_by('-created_at')
    
    context = {
        'notifications': notifications,
        'action': 'notifications',
        'user': request.user
    }
    return render(request, 'account/demo/notifications.html', context)

@login_required
def mark_notifications_read(request):
    if request.method == "POST":
        request.user.notifications.filter(is_read=False).update(is_read=True)
        if request.headers.get('HX-Request'):
            return HttpResponse("")
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)

@login_required
def delete_notification(request, notif_id):
    if request.method == "POST" or request.method == "DELETE":
        try:
            notif = request.user.notifications.get(id=notif_id)
            notif.delete()
            if request.headers.get('HX-Request'):
                return HttpResponse("")
            return JsonResponse({"status": "success"})
        except Exception:
            if request.headers.get('HX-Request'):
                return HttpResponse("Not found", status=404)
            return JsonResponse({"status": "error"}, status=404)
    return JsonResponse({"status": "error"}, status=400)

@login_required
def bulk_delete_notifications(request):
    if request.method == "POST":
        notification_ids = request.POST.getlist('notification_ids')
        if notification_ids:
            request.user.notifications.filter(id__in=notification_ids).delete()
        if request.headers.get('HX-Request'):
            return HttpResponse("")
        return redirect(reverse('user_dashboard') + "?section=notifications")
    return JsonResponse({"status": "error"}, status=400)


@login_required
def user_traffic_api(request):
    try:
        days = int(request.GET.get('days', 7))
    except ValueError:
        days = 7

    start_date = timezone.now().date() - timedelta(days=days-1)
    
    from blog_post.models import Post_view_ip
    from forum.models import Question_view_ip
    
    labels = []
    visits_data = []
    users_data = []
    
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        
        if current_date == timezone.now().date():
            label = 'Today'
        else:
            label = current_date.strftime('%b %d')
            
        labels.append(label)
        
        post_views = Post_view_ip.objects.filter(post__author=request.user, viewed_at=current_date)
        question_views = Question_view_ip.objects.filter(question__author=request.user, viewed_at=current_date)
        
        total_visits = post_views.count() + question_views.count()
        
        post_ips = set(post_views.values_list('ip_address', flat=True))
        question_ips = set(question_views.values_list('ip_address', flat=True))
        unique_users = len(post_ips.union(question_ips))
        
        visits_data.append(total_visits)
        users_data.append(unique_users)
        
    return JsonResponse({
        'labels': labels,
        'visits': visits_data,
        'users': users_data
    })

from blog_post.models import CompanyService, CompanyClientFocus, CompanyClient, CompanyLocation
from blog_post.forms import CompanyServiceForm, CompanyClientFocusForm, CompanyClientForm, CompanyLocationForm

@login_required
def manage_company_view(request, company_id):
    company = get_object_or_404(BlogPost, pk=company_id, author=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_service':
            form = CompanyServiceForm(request.POST)
            if form.is_valid():
                service = form.save(commit=False)
                service.company = company
                service.save()
                messages.success(request, "Service added successfully.")
        
        elif action == 'add_focus':
            form = CompanyClientFocusForm(request.POST)
            if form.is_valid():
                focus = form.save(commit=False)
                focus.company = company
                focus.save()
                messages.success(request, "Client focus added successfully.")
                
        elif action == 'add_client':
            form = CompanyClientForm(request.POST)
            if form.is_valid():
                client = form.save(commit=False)
                client.company = company
                client.save()
                messages.success(request, "Client added successfully.")
                
        elif action == 'add_location':
            form = CompanyLocationForm(request.POST)
            if form.is_valid():
                location = form.save(commit=False)
                location.company = company
                location.save()
                messages.success(request, "Location added successfully.")
                
        return redirect('manage_company', company_id=company.id)
        
    context = {
        'company': company,
        'service_form': CompanyServiceForm(),
        'focus_form': CompanyClientFocusForm(),
        'client_form': CompanyClientForm(),
        'location_form': CompanyLocationForm(),
    }
    return render(request, 'account/demo/manage_company.html', context)

@login_required
def delete_company_item_view(request, company_id, item_type, item_id):
    company = get_object_or_404(BlogPost, pk=company_id, author=request.user)
    
    if request.method == 'POST':
        if item_type == 'service':
            item = get_object_or_404(CompanyService, pk=item_id, company=company)
        elif item_type == 'focus':
            item = get_object_or_404(CompanyClientFocus, pk=item_id, company=company)
        elif item_type == 'client':
            item = get_object_or_404(CompanyClient, pk=item_id, company=company)
        elif item_type == 'location':
            item = get_object_or_404(CompanyLocation, pk=item_id, company=company)
        else:
            return redirect('manage_company', company_id=company.id)
            
        item.delete()
        messages.success(request, f"{item_type.capitalize()} deleted successfully.")
        
    return redirect('manage_company', company_id=company.id)


@login_required
def user_company_edit_view(request, pk):
    """Redirect to user dashboard section=edit-company."""
    return redirect(f"{reverse('user_dashboard')}?section=edit-company&company_id={pk}")
