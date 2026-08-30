import hashlib
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
        ]

    def clean(self):
        cleaned_data = super().clean()
        title = cleaned_data.get("title") or getattr(self.instance, "title", "")
        description = cleaned_data.get("description") or getattr(self.instance, "description", "")
        if title:
            raw_content = (title + str(description or "")).encode("utf-8")
            c_hash = hashlib.md5(raw_content).hexdigest()
            qs = BlogPost.objects.filter(content_hash=c_hash)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A blog post with duplicate content already exists.")

        featured_image = cleaned_data.get("featured_image")
        if featured_image and hasattr(featured_image, "read"):
            try:
                featured_image.seek(0)
                img_bytes = featured_image.read()
                featured_image.seek(0)
                img_hash = hashlib.md5(img_bytes).hexdigest()
                img_qs = BlogPost.objects.filter(image_hash=img_hash)
                if self.instance and self.instance.pk:
                    img_qs = img_qs.exclude(pk=self.instance.pk)
                if img_qs.exists():
                    raise forms.ValidationError("A blog post with a duplicate image already exists.")
            except Exception:
                pass

        return cleaned_data

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
