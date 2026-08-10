from django import forms

from tags.models import Tag
from .models import BlogPost, Category


class IconForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "font_awesome_icon" , "description"]


class BlogPostForm(forms.ModelForm):
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=True)
    tags = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "post_tags_hidden"}),
    )
    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "id": "post_description",
                "rows": 12,
                "class": "ft-input w-full",
                # CKEditor 5 replaces this textarea on the client side
            }
        ),
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

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            self._save_tags()
        else:
            # If commit=False, override save_m2m so that tags are saved when save_m2m is called
            original_save_m2m = self.save_m2m
            def save_m2m_override():
                original_save_m2m()
                self._save_tags()
            self.save_m2m = save_m2m_override
        return instance

    def _save_tags(self):
        tags_str = self.cleaned_data.get('tags', '')
        tag_objs = []
        if tags_str:
            tag_names = [t.strip() for t in tags_str.split(',') if t.strip()]
            for name in tag_names:
                # get or create tag (case-insensitive)
                tag, created = Tag.objects.get_or_create(name__iexact=name, defaults={"name": name})
                tag_objs.append(tag)
        self.instance.tags.set(tag_objs)
