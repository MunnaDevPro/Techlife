from django.db import models
from ckeditor.fields import RichTextField

class Advertisement(models.Model):
    
    POSITION_CHOICES = [
        (1, 'After Hero Section'),
        (2, 'After Blog Grid'),
        (3, 'After Latest News'),
        (4, 'After Particular Category'),
        (5, 'After Most View'),
        (6, 'After Marquee'),
        (7, 'Popular sidebar'),
        (8, 'Category Details page'),
        (9, 'Under Top question (hero section)'),
        (10, 'Category page add(left side)')

    ]
    
    title = models.CharField(max_length=200)
    ad_code = RichTextField()
    order = models.PositiveIntegerField(
        choices=POSITION_CHOICES,
        unique=True,
        help_text="Select which section this ad should appear after"    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Advertisement"
        verbose_name_plural = "Advertisements"

    def __str__(self):
        return f"Ad {self.order} - {self.title}"