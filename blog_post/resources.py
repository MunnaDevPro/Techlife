
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from django.utils.text import slugify
from django.db import transaction

from .models import Category, SubCategory, BlogPost, Tag, compnay_logo, BlogAdditionalImage
from accounts.models import CustomUserModel


class CategoryResource(resources.ModelResource):
    """Resource for Category import/export"""
    
    class Meta:
        model = Category
        import_id_fields = ('name',) 
        fields = ('id', 'name', 'slug', 'font_awesome_icon', 'description')
        skip_unchanged = True
        report_skipped = True


class SubCategoryResource(resources.ModelResource):
    """Resource for SubCategory import/export"""
    
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(Category, 'name') 
    )

    class Meta:
        model = SubCategory
        fields = ('id', 'category', 'name', 'slug', 'description')
        skip_unchanged = True
        report_skipped = True


class BlogPostResource(resources.ModelResource):
    """
    Resource for BlogPost import/export
    Handles CSV import with proper validation and status preservation
    """
    
    category = fields.Field(
        column_name='category', 
        attribute='category', 
        widget=ForeignKeyWidget(Category, 'name')
    )
    subcategory = fields.Field(
        column_name='subcategory', 
        attribute='subcategory', 
        widget=ForeignKeyWidget(SubCategory, 'name')
    )
    author = fields.Field(
        column_name='author', 
        attribute='author', 
        widget=ForeignKeyWidget(CustomUserModel, 'email')
    )
    tags = fields.Field(
        column_name='tags', 
        attribute='tags', 
        widget=ManyToManyWidget(Tag, field='name', separator=',')
    )

    class Meta:
        model = BlogPost
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True
        fields = (
            'id', 'title', 'subtitle', 'slug', 'description', 
            'featured_image_url', 'category', 'subcategory', 
            'author', 'status', 'views', 'tags'
        )
        use_bulk = False  
        
    def skip_row(self, instance, original, row, import_validation_errors=None):
        """
        Skip rows with missing required fields
        Returns True if the row should be skipped
        """
        if not row.get('title') or str(row.get('title')).strip() == '':
            print(f" Skipping row - Missing title")
            return True
            
        if not row.get('author') or str(row.get('author')).strip() == '':
            print(f" Skipping row - Missing author")
            return True
            
        if not row.get('description') or str(row.get('description')).strip() == '':
            print(f" Skipping row - Missing description")
            return True
            
        return super().skip_row(instance, original, row, import_validation_errors)

    def before_import_row(self, row, **kwargs):
        """
        Clean and prepare data before import
        This runs before each row is processed
        """
        if not row.get('slug') or str(row.get('slug')).strip() == '':
            if row.get('title'):
                row['slug'] = slugify(str(row.get('title')))
        
        valid_statuses = ['pending', 'edited', 'published', 'rejected']
        if not row.get('status') or str(row.get('status')).strip() == '':
            row['status'] = 'pending'
        elif row.get('status') not in valid_statuses:
            print(f" Invalid status '{row.get('status')}', setting to 'pending'")
            row['status'] = 'pending'
        
        if not row.get('views') or str(row.get('views')).strip() == '':
            row['views'] = 0
        else:
            try:
                row['views'] = int(row['views'])
            except (ValueError, TypeError):
                row['views'] = 0
        
        if row.get('category') and str(row.get('category')).strip() == '':
            row['category'] = None
        if row.get('subcategory') and str(row.get('subcategory')).strip() == '':
            row['subcategory'] = None
            
        if row.get('description'):
            row['description'] = str(row.get('description')).strip()
            
        # Clean featured_image_url
        if row.get('featured_image_url') and str(row.get('featured_image_url')).strip() == '':
            row['featured_image_url'] = None
            
        print(f" Processing: {row.get('title')} (ID: {row.get('id')}) - Status: {row.get('status')}")
    
    def save_instance(self, instance, is_create, using_transactions=True, dry_run=False):
        """
        Save the instance with skip_auto_status flag to prevent 
        the model's save() method from overriding the status
        """
        if not dry_run:
            try:
                with transaction.atomic():
                    instance.save(skip_auto_status=True)
                    print(f" Saved: {instance.title} with status '{instance.status}'")
            except Exception as e:
                print(f" Error saving instance: {e}")
                raise
    
    def after_import_row(self, row, row_result, **kwargs):
        """
        Double check that status was saved correctly after import
        This is a safety check to ensure status wasn't changed
        """
        if row_result.import_type != 'skip' and row.get('status'):
            try:
                instance = BlogPost.objects.get(id=row['id'])
                
                if instance.status != row['status']:
                    print(f" Status mismatch detected for '{instance.title}'. Fixing...")
                    BlogPost.objects.filter(id=row['id']).update(status=row['status'])
                    print(f" Status corrected to '{row['status']}'")
                else:
                    print(f" Status verified: {instance.title} = '{instance.status}'")
                    
            except BlogPost.DoesNotExist:
                print(f" Post with ID {row['id']} not found after import")
            except Exception as e:
                print(f" Error in after_import_row: {e}")


class AdminBlogPostResource(BlogPostResource):
    """Resource for administrative export including full source and automation metadata"""

    class Meta(BlogPostResource.Meta):
        fields = BlogPostResource.Meta.fields + (
            'source_name', 'source_url', 'source_author', 'source_published_at',
            'original_title', 'original_content_hash', 'automation_id',
            'generated_by_ai', 'ai_model', 'reviewer_model', 'review_decision',
            'quality_score', 'factual_accuracy_score', 'language_score',
            'seo_score', 'review_notes', 'source_image_url',
            'image_processing_status', 'automation_created_at'
        )


class CompanyLogoResource(resources.ModelResource):
    """Resource for Company Logo import/export"""
    
    class Meta:
        model = compnay_logo
        fields = ('id', 'name', 'company_image', 'company_image_url')
        skip_unchanged = True


class BlogAdditionalImageResource(resources.ModelResource):
    """Resource for Blog Additional Images import/export"""
    
    blog = fields.Field(
        column_name='blog_title',
        attribute='blog',
        widget=ForeignKeyWidget(BlogPost, 'title')
    )
    
    class Meta:
        model = BlogAdditionalImage
        fields = ('id', 'blog', 'additional_image', 'additional_image_url')
        skip_unchanged = True