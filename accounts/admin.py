# app_name/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe 
from .models import CustomUserModel 

@admin.register(CustomUserModel)
class CustomUserAdmin(UserAdmin):

    actions = ['delete_selected']

    list_display = (
        'user_photo',  
        'email', 
        'first_name', 
        'last_name', 
        'is_verified', 
        'is_staff', 
    )
    list_display_links = ('email',)
    ordering = ('email',) 

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'mobile', 'profile_picture')}),
        ('Address', {'fields': ('address_line_1', 'address_line_2', 'city', 'postcode', 'country')}),
        ('Permissions', {'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    

    def user_photo(self, obj):

        if obj.profile_picture:
            img_url = obj.profile_picture.url

            img_url = obj.profile_picture.url 
            
        # Return safe HTML for the image thumbnail
        return mark_safe(
            f'<img src="{img_url}" width="40" height="40" style="border-radius: 50%; object-fit: cover; border: 1px solid #ccc;" />'
        )

    user_photo.short_description = 'Photo' 
    
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_verified', 'is_staff', 'is_superuser', 'created_at')