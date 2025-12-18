from django.shortcuts import render
from blog_post.models import BlogPost
from forum.models import Question, Answer
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required

def questions(request, slug):
    blogs = BlogPost.objects.all().order_by('-created_at')
    particular_question = Question.objects.select_related('author').prefetch_related('answers__author').get(slug=slug)


    # search filter
    answers = particular_question.answers.all()

    query = request.GET.get('q')    
    if query:
        answers = Answer.objects.filter(
            Q(content__icontains=query)
        ).distinct()
       



    # filter for sort by
    sort_by = request.GET.get('sort', 'best')

    if sort_by == 'old':
        answers = particular_question.answers.all().order_by('created_at')
    elif sort_by == 'top':
        answers = particular_question.answers.all().order_by('-created_at') 
    elif sort_by == 'recently':
        answers = particular_question.answers.all().order_by('-created_at')[:5] 


    #paginator section
    paginator = Paginator(answers, 5)
    page_number = request.GET.get('page')
    paginator_answer = paginator.get_page(page_number) 

    context = {
        "blogs":blogs,
        "answers":answers,
        "particular_question":particular_question,
        'current_sort': sort_by.capitalize(),
        "paginator_answer":paginator_answer
    }

    return render(request, "forum/question_page.html",context)


def questions_list(request):
    blogs = BlogPost.objects.all().order_by("-created_at")
    questions = Question.objects.select_related('author').prefetch_related('answers').all()    


    query = request.GET.get('q')
    if query:
        questions = questions.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )


    sort = request.GET.get('sort', 'latest')
    if sort == 'top':
        questions = questions.annotate(ans_count=Count('answers')).order_by('-ans_count')
    elif sort == 'best':
        questions = questions.annotate(ans_count=Count('answers')).order_by('-ans_count', '-created_at')
    elif sort == 'new' or sort == 'latest':
        questions = questions.order_by("-created_at")
  

    paginator = Paginator(questions, 2) 
    page_number = request.GET.get('page')
    questions = paginator.get_page(page_number)

    context = {
        "blogs":blogs,
        "questions" :questions,
    
    }
    return render(request, "forum/all_question.html", context)


def post_answer(request, slug):
    if request.method == "POST":
        question  = get_object_or_404(Question, slug=slug)
        content = request.POST.get('content')

        if content:
            Answer.objects.create(
                question=question,
                author=request.user,
                content=content
            )
            return redirect('questions', slug=slug)
        
    return redirect('questions', slug=slug)

def create_question(request):

    if not request.user.is_authenticated:
        return redirect("questions_list")
    
    if request.method == "POST":
        title = request.POST.get('title')
        content = request.POST.get('content')
        image = request.FILES.get('image')

    
        if title and content:
            Question.objects.create(
                author=request.user,
                title=title,
                content=content,
                image=image
            )
            return redirect('questions_list')
    return redirect('questions_list')