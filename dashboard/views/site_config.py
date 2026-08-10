from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import dateparse

from dashboard.permissions import staff_required
from dashboard.views.views import get_dashboard_context
from google_add.models import Advertisement
from blog_post.models import compnay_logo
from contact.models import FooterSettings
from maintenance.models import MaintenanceSettings

# 1. Ads Configuration View
@staff_required
def ads_config(request):
    """CRUD interface for google_add Advertisement models."""
    if request.method == "POST":
        action = request.POST.get('action')
        if action == "save":
            ad_id = request.POST.get('id')
            title = request.POST.get('title')
            ad_code = request.POST.get('ad_code')
            order = request.POST.get('order')
            is_active = request.POST.get('is_active') == 'true'
            
            from django.db import IntegrityError
            try:
                if ad_id:
                    ad = get_object_or_404(Advertisement, pk=ad_id)
                    ad.title = title
                    ad.ad_code = ad_code
                    ad.order = int(order)
                    ad.is_active = is_active
                    ad.save()
                    messages.success(request, "Advertisement updated.")
                else:
                    Advertisement.objects.create(
                        title=title,
                        ad_code=ad_code,
                        order=int(order),
                        is_active=is_active
                    )
                    messages.success(request, "Advertisement created.")
            except IntegrityError:
                messages.error(request, "An advertisement for this position already exists. Please choose a different position or edit the existing one.")
        elif action == "delete":
            ad_id = request.POST.get('id')
            get_object_or_404(Advertisement, pk=ad_id).delete()
            messages.success(request, "Advertisement deleted.")
            
        return redirect("dashboard:settings_ads")
        
    ads = Advertisement.objects.all().order_by('order')
    ctx = get_dashboard_context(request, "Ad Settings", "Site Settings", "dashboard:settings_ads")
    ctx.update({
        "ads": ads,
        "positions": Advertisement.POSITION_CHOICES,
    })
    return render(request, "dashboard/site_config/ads.html", ctx)

def validate_image_file(image):
    if not image:
        return
    valid_mime_types = ['image/jpeg', 'image/png', 'image/webp']
    if hasattr(image, 'content_type') and image.content_type not in valid_mime_types:
        raise ValueError("Invalid file type. Only JPG, PNG, and WEBP images are allowed.")
    if image.size > 5 * 1024 * 1024:
        raise ValueError("File size too large. Maximum allowed size is 5MB.")

# 2. Footer / Company Logos View
@staff_required
def footer_logo_config(request):
    """CRUD interface for footer configuration and company logos."""
    footer_set = FooterSettings.objects.first()
    if not footer_set:
        # Create default
        footer_set = FooterSettings.objects.create(
            description="Techlife description text.",
            email="contact@techlife.com",
            phone="+8801700895489",
            address="Dhaka, Bangladesh"
        )
        
    if request.method == "POST":
        action = request.POST.get('action')
        if action == "save_footer":
            footer_set.description = request.POST.get('description')
            footer_set.email = request.POST.get('email')
            footer_set.phone = request.POST.get('phone')
            footer_set.address = request.POST.get('address')
            footer_set.facebook_url = request.POST.get('facebook_url')
            footer_set.twitter_url = request.POST.get('twitter_url')
            footer_set.linkedin_url = request.POST.get('linkedin_url')
            footer_set.whatsapp_number = request.POST.get('whatsapp_number')
            footer_set.developer_company_name = request.POST.get('developer_company_name')
            footer_set.developer_company_url = request.POST.get('developer_company_url')
            
            if 'logo' in request.FILES:
                try:
                    validate_image_file(request.FILES['logo'])
                    footer_set.logo = request.FILES['logo']
                except ValueError as ve:
                    messages.error(request, str(ve))
                    return redirect("dashboard:settings_footer")
                
            footer_set.save()
            messages.success(request, "Footer configuration saved.")
            
        elif action == "add_logo":
            name = request.POST.get('name')
            url = request.POST.get('company_image_url')
            img = request.FILES.get('company_image')
            
            if img:
                try:
                    validate_image_file(img)
                except ValueError as ve:
                    messages.error(request, str(ve))
                    return redirect("dashboard:settings_footer")
            
            compnay_logo.objects.create(
                name=name,
                company_image=img,
                company_image_url=url
            )
            messages.success(request, "Company logo added.")
            
        elif action == "delete_logo":
            logo_id = request.POST.get('id')
            get_object_or_404(compnay_logo, pk=logo_id).delete()
            messages.success(request, "Company logo deleted.")
            
        return redirect("dashboard:settings_footer")
        
    logos = compnay_logo.objects.all().order_by('name')
    ctx = get_dashboard_context(request, "Footer Management", "Site Settings", "dashboard:settings_footer")
    ctx.update({
        "footer": footer_set,
        "logos": logos,
    })
    return render(request, "dashboard/site_config/footer.html", ctx)

# 3. Maintenance Mode View
@staff_required
def maintenance_config(request):
    """Toggle maintenance settings flags."""
    m_settings = MaintenanceSettings.get()
    
    if request.method == "POST":
        site_maintenance = request.POST.get('site_under_maintenance') == 'true'
        forum_maintenance = request.POST.get('forum_under_maintenance') == 'true'
        until_str = request.POST.get('maintenance_until')
        
        m_settings.site_under_maintenance = site_maintenance
        m_settings.forum_under_maintenance = forum_maintenance
        
        if until_str:
            m_settings.maintenance_until = dateparse.parse_datetime(until_str)
        else:
            m_settings.maintenance_until = None
            
        m_settings.custom_message = request.POST.get('custom_message') or None
            
        m_settings.save()
        messages.success(request, f"Maintenance configuration updated. Site Maintenance: {'ON' if site_maintenance else 'OFF'}.")
        return redirect("dashboard:settings_maintenance")
        
    ctx = get_dashboard_context(request, "Maintenance Mode", "Site Settings", "dashboard:settings_maintenance")
    ctx.update({
        "settings": m_settings,
    })
    return render(request, "dashboard/site_config/maintenance.html", ctx)
