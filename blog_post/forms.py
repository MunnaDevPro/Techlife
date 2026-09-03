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


from .models import Review

class ReviewSearchForm(forms.Form):
    query = forms.CharField(
        label="Search company or software", 
        max_length=200, 
        required=False, 
        widget=forms.TextInput(attrs={
            "placeholder": "Search the company or software you worked with...", 
            "class": "w-full rounded-full border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-6 py-4"
        })
    )

class ReviewRatingForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['quality_rating', 'communication_rating', 'timeliness_rating']
        labels = {
            'quality_rating': 'Quality',
            'communication_rating': 'Communication',
            'timeliness_rating': 'Timeliness',
        }
        widgets = {
            'quality_rating': forms.Select(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3'}),
            'communication_rating': forms.Select(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3'}),
            'timeliness_rating': forms.Select(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3'}),
        }

class ReviewDetailsForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['title', 'body']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3', 
                'placeholder': 'Summarize your experience...'
            }),
            'body': forms.Textarea(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3', 
                'rows': 5, 
                'placeholder': 'Tell us more about your experience...'
            }),
        }

class ReviewIdentityForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['is_anonymous']
        labels = {
            'is_anonymous': 'Submit anonymously (Your name will not be displayed publicly)'
        }
        widgets = {
            'is_anonymous': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500'}),
        }


class CompanyStep1Form(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_company_category=True).order_by('name'), 
        required=True,
        widget=forms.Select(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] focus:ring-2 focus:ring-[#1e3a6e]/20 transition-all duration-200 text-sm p-3.5 cursor-pointer'})
    )

    class Meta:
        model = BlogPost
        fields = ['title', 'subtitle', 'company_email', 'company_phone', 'category', 'subcategory']
        labels = {
            'category': 'Company Industry',
            'subcategory': 'Industry Sector',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] focus:ring-2 focus:ring-[#1e3a6e]/20 transition-all duration-200 text-sm p-3.5', 'placeholder': 'Company Name'}),
            'subtitle': forms.TextInput(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] focus:ring-2 focus:ring-[#1e3a6e]/20 transition-all duration-200 text-sm p-3.5', 'placeholder': 'A brief tagline...'}),
            'company_email': forms.EmailInput(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] focus:ring-2 focus:ring-[#1e3a6e]/20 transition-all duration-200 text-sm p-3.5', 'placeholder': 'contact@company.com'}),
            'company_phone': forms.TextInput(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] focus:ring-2 focus:ring-[#1e3a6e]/20 transition-all duration-200 text-sm p-3.5', 'placeholder': '+1 (555) 000-0000'}),
            'subcategory': forms.Select(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] focus:ring-2 focus:ring-[#1e3a6e]/20 transition-all duration-200 text-sm p-3.5 cursor-pointer'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].label = "Company Industry"
        self.fields['category'].empty_label = "Select Company Industry"
        self.fields['category'].required = True
        self.fields['subcategory'].label = "Industry Sector"
        self.fields['subcategory'].empty_label = "Select Industry Sector (Optional)"


class PublicCompanyRegistrationForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_company_category=True).order_by('name'), 
        required=True,
        label="Company Industry",
        widget=forms.Select(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] focus:ring-2 focus:ring-[#1e3a6e]/20 transition-all duration-200 text-sm p-3.5 cursor-pointer'})
    )

    class Meta:
        model = BlogPost
        fields = [
            'title', 
            'subtitle', 
            'company_email', 
            'company_phone', 
            'category', 
            'subcategory',
            'description',
            'featured_image',
            'trade_license'
        ]
        labels = {
            'category': 'Company Industry',
            'subcategory': 'Industry Sector',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] focus:ring-2 focus:ring-[#1e3a6e]/20 transition-all duration-200 text-sm p-3.5', 'placeholder': 'Company / Business Name'}),
            'subtitle': forms.TextInput(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] focus:ring-2 focus:ring-[#1e3a6e]/20 transition-all duration-200 text-sm p-3.5', 'placeholder': 'Tagline or short slogan...'}),
            'company_email': forms.EmailInput(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] focus:ring-2 focus:ring-[#1e3a6e]/20 transition-all duration-200 text-sm p-3.5', 'placeholder': 'contact@company.com'}),
            'company_phone': forms.TextInput(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] focus:ring-2 focus:ring-[#1e3a6e]/20 transition-all duration-200 text-sm p-3.5', 'placeholder': '+1 (555) 000-0000'}),
            'subcategory': forms.Select(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] focus:ring-2 focus:ring-[#1e3a6e]/20 transition-all duration-200 text-sm p-3.5 cursor-pointer'}),
            'description': forms.Textarea(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] focus:ring-2 focus:ring-[#1e3a6e]/20 transition-all duration-200 text-sm p-4', 'rows': 5, 'placeholder': 'Brief description about your company...'}),
            'featured_image': forms.FileInput(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] text-sm p-2.5 cursor-pointer', 'accept': 'image/*'}),
            'trade_license': forms.FileInput(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] text-sm p-2.5 cursor-pointer', 'accept': '.pdf,image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].label = "Company Industry"
        self.fields['category'].empty_label = "Select Company Industry"
        self.fields['category'].required = True
        self.fields['subcategory'].label = "Industry Sector"
        self.fields['subcategory'].empty_label = "Select Industry Sector (Optional)"

class CompanyStep2Form(forms.ModelForm):
    # tags = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm p-3', 'placeholder': 'Tags separated by commas'}))
    class Meta:
        model = BlogPost
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'w-full rounded-lg border border-gray-300 bg-white focus:border-[#1e3a6e] focus:ring-2 focus:ring-[#1e3a6e]/20 transition-all duration-200 text-sm p-4', 'rows': 8, 'placeholder': 'Detailed company description...'}),
        }

class CompanyStep3Form(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['featured_image', 'trade_license']
        widgets = {
            'featured_image': forms.FileInput(attrs={'class': 'absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10', 'accept': 'image/*'}),
            'trade_license': forms.FileInput(attrs={'class': 'absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10', 'accept': '.pdf,image/*'}),
        }

from .models import CompanyService, CompanyClientFocus, CompanyClient, CompanyLocation

class CompanyServiceForm(forms.ModelForm):
    class Meta:
        model = CompanyService
        fields = ['name', 'percentage']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#1e3a6e] focus:ring-[#1e3a6e] sm:text-sm p-2', 'placeholder': 'Service Name (e.g. Web Development)'}),
            'percentage': forms.NumberInput(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#1e3a6e] focus:ring-[#1e3a6e] sm:text-sm p-2', 'placeholder': 'Percentage (0-100)'}),
        }

class CompanyClientFocusForm(forms.ModelForm):
    class Meta:
        model = CompanyClientFocus
        fields = ['name', 'percentage']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#1e3a6e] focus:ring-[#1e3a6e] sm:text-sm p-2', 'placeholder': 'Focus (e.g. Small Business)'}),
            'percentage': forms.NumberInput(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#1e3a6e] focus:ring-[#1e3a6e] sm:text-sm p-2', 'placeholder': 'Percentage (0-100)'}),
        }

class CompanyClientForm(forms.ModelForm):
    class Meta:
        model = CompanyClient
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#1e3a6e] focus:ring-[#1e3a6e] sm:text-sm p-2', 'placeholder': 'Client Name'}),
        }

class CompanyLocationForm(forms.ModelForm):
    class Meta:
        model = CompanyLocation
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-[#1e3a6e] focus:ring-[#1e3a6e] sm:text-sm p-2', 'placeholder': 'Location (e.g. Dhaka, Bangladesh)'}),
        }


class CompanyProfileForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_company_category=True).order_by('name'), 
        required=True,
        label="Company Industry",
        widget=forms.Select(attrs={"class": "ft-input w-full cursor-pointer"})
    )
    tags = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "post_tags_hidden"}),
    )
    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "id": "post_description",
                "rows": 8,
                "class": "ft-input w-full",
            }
        ),
        required=False,
    )

    class Meta:
        model = BlogPost
        fields = [
            "title",
            "subtitle",
            "company_email",
            "company_phone",
            "company_website",
            "trade_license",
            "featured_image",
            "description",
            "company_founded_year",
            "company_employees_count",
            "company_hourly_rate",
            "company_min_project_size",
            "category",
            "subcategory",
        ]
        labels = {
            'category': 'Company Industry',
            'subcategory': 'Industry Sector',
        }
        widgets = {
            'subcategory': forms.Select(attrs={'class': 'ft-input w-full cursor-pointer'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].label = "Company Industry"
        self.fields['category'].empty_label = "Select Company Industry"
        if 'subcategory' in self.fields:
            self.fields['subcategory'].label = "Industry Sector"
            self.fields['subcategory'].empty_label = "Select Industry Sector (Optional)"

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            self._save_tags()
        else:
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
                tag, created = Tag.objects.get_or_create(name__iexact=name, defaults={"name": name})
                tag_objs.append(tag)
        self.instance.tags.set(tag_objs)
