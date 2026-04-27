from django import forms
from django.core.validators import MinLengthValidator

from ckeditor_uploader.widgets import CKEditorUploadingWidget

from tags.models import Tag
from .models import BlogPost, Category


class IconForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "font_awesome_icon" , "description"]


class BlogPostForm(forms.ModelForm):
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=True)
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Tags",
    )
    description = forms.CharField(
        widget=CKEditorUploadingWidget(
            attrs={
                "id": "post_description",
                "rows": 12,
                "class": (
                    "django-ckeditor-widget w-full bg-gray-50 border border-gray-200 "
                    "rounded-xl px-4 py-3 text-[13px] text-gray-800"
                ),
            }
        ),
        validators=[
            MinLengthValidator(
                2000, message="Description must be at least 2000 characters."
            )
        ],
        required=False,
    )

    class Meta:
        model = BlogPost
        fields = [
            "title",
            "description",
            "featured_image",
            "featured_image_url",
            "category",
            "subcategory",
            "tags",
        ]
