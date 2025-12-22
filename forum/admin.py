from django.contrib import admin
from .models import Question, Answer, Follow_section


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 1
    fields = ('author', 'content', 'created_at')
    readonly_fields = ('created_at',)
    show_change_link = True


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
    list_display = ('title', 'author', 'created_at')
    search_fields = ('title', 'content', 'author__username')
    list_filter = ('created_at', 'author')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    inlines = [AnswerInline]
    ordering = ('-created_at',)
    list_per_page = 20

    fieldsets = (
        ('Question Info', {
            'fields': ('title', 'slug', 'content', 'image')
        }),
        ('Author & Meta', {
            'fields': ('author', 'created_at', )
        }),
    )


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'author', 'created_at')
    search_fields = ('content', 'author__username', 'question__title')
    list_filter = ('created_at', 'author')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

admin.site.register(Follow_section)