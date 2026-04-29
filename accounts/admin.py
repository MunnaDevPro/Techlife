# app_name/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.conf import settings
from django.utils.safestring import mark_safe 
from unfold.admin import ModelAdmin
from .models import CustomUserModel 

@admin.register(CustomUserModel)
class CustomUserAdmin(ModelAdmin, UserAdmin):

    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

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
    readonly_fields = ('last_login', 'date_joined', 'created_at', 'updated_at')

    add_fieldsets = (
        ('Account', {
            'classes': ('tab',),
            'fields': ('email', 'password1', 'password2'),
        }),
        ('Personal info', {
            'classes': ('tab',),
            'fields': ('first_name', 'last_name', 'mobile', 'profile_picture'),
        }),
        ('Address', {
            'classes': ('tab',),
            'fields': ('address_line_1', 'address_line_2', 'city', 'postcode', 'country'),
        }),
        ('Permissions', {
            'classes': ('tab',),
            'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
    )

    fieldsets = (
        ('Account', {
            'classes': ('tab',),
            'fields': ('email', 'password'),
        }),
        ('Personal info', {
            'classes': ('tab',),
            'fields': ('first_name', 'last_name', 'mobile', 'profile_picture'),
        }),
        ('Address', {
            'classes': ('tab',),
            'fields': ('address_line_1', 'address_line_2', 'city', 'postcode', 'country'),
        }),
        ('Permissions', {
            'classes': ('tab',),
            'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('System info', {
            'classes': ('tab',),
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
        }),
    )
    

    def user_photo(self, obj):
        img_url = obj.profile_picture.url if obj.profile_picture else f"{settings.MEDIA_URL}user_profile/default_user_profile.png"

        return mark_safe(
            f'<img src="{img_url}" width="40" height="40" style="border-radius: 50%; object-fit: cover; border: 1px solid #ccc;" />'
        )

    user_photo.short_description = 'Photo' 
    
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_verified', 'is_staff', 'is_superuser', 'created_at')