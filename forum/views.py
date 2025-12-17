from django.shortcuts import render
from blog_post.models import BlogPost
from forum.models import Question
def questions(request, slug):
    blogs = BlogPost.objects.all().order_by('-created_at')
    particular_question = Question.objects.select_related('author').prefetch_related('answers__author').get(slug=slug)
    context = {
        "blogs":blogs,
        "particular_question":particular_question
    }
    # if request.headers.get('HX-Request'):
    #     return render(request, "forum/partial_question.html",context)
    return render(request, "forum/question_page.html",context)


def questions_list(request):
    blogs = BlogPost.objects.all().order_by("-created_at")
    questions = Question.objects.select_related('author').prefetch_related('answers').all()    
    context = {
        "blogs":blogs,
        "questions" :questions,
    
    }
    return render(request, "forum/all_question.html", context)
