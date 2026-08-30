from django.db import models
from accounts.models import CustomUserModel
from django.utils.text import slugify
from ckeditor_uploader.fields import RichTextUploadingField
from imagekit.models import ImageSpecField, ProcessedImageField
from imagekit.processors import ResizeToFill, Adjust, ResizeToFit

class Question(models.Model):
    author = models.ForeignKey(CustomUserModel, on_delete=models.CASCADE, related_name='questions',default=1)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=500,blank=True,null=True,unique=True,db_index=True,)
    content = RichTextUploadingField(blank=True, null=True)
    image = ProcessedImageField(
        upload_to="question_images/",
        processors=[ResizeToFit(1000, 700)],
        format="WEBP",
        options={"quality": 80},
        blank=True,
        null=True,
    )
    image_thumbnail = ImageSpecField(
            source='image',
        processors=[ResizeToFill(550,380),Adjust(sharpness=1)],
        format='WEBP',
        options={'quality': 90}
        )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Question"
        verbose_name_plural = "Questions"



    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

            original_slug = self.slug
            counter = 1
            while Question.objects.filter(slug=self.slug).exists():
                self.slug = f'{original_slug}-{counter}'
                counter += 1
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.author.first_name} {self.author.last_name}"


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    author = models.ForeignKey(CustomUserModel,on_delete=models.CASCADE,related_name='answers')
    content = models.TextField()
    image = ProcessedImageField(
        upload_to="answers_images/",
        processors=[ResizeToFit(1000, 700)],
        format="WEBP",
        options={"quality": 80},
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Answer"
        verbose_name_plural = "Answers"

    def __str__(self):
        return f"Answer by {self.author} on '{self.question.title}'"





class Question_view_ip(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="view_track"
    )
    user = models.ForeignKey(
        CustomUserModel, on_delete=models.CASCADE, null=True, blank=True
    )
    ip_address = models.CharField(max_length=255, null=True, blank=True)
    viewed_at = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ("question", "ip_address")

    def __str__(self):
        return f"{self.question.title} viewed by {self.user or self.ip_address}"

class Follow_section(models.Model):
    user = models.OneToOneField(CustomUserModel, on_delete=models.CASCADE)
    
    following = models.ManyToManyField(CustomUserModel, related_name='followers', blank=True)


    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    def followers_count(self):
        return self.user.followers.count()

    def following_count(self):
        return self.following.count()
    
    def __str__(self):
        return f"Follow Section of {self.user.username}"
