from django.shortcuts import render
from blog_post.models import BlogPost
from forum.models import Question, Answer
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from accounts.models import CustomUserModel
def questions(request, slug):
    blogs = BlogPost.objects.all().order_by('-created_at')
    particular_question = Question.objects.select_related('author').prefetch_related('answers__author').get(slug=slug)

    right_side_questions = Question.objects.select_related('author').prefetch_related('answers').all() 



    # search filter
    answers = particular_question.answers.all()

    query = request.GET.get('q')    
    if query:
        answers = particular_question.answers.filter(
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
        "paginator_answer":paginator_answer,

        "right_side_questions" : right_side_questions,
    }

    return render(request, "forum/question_page.html",context)


def questions_list(request):
    blogs = BlogPost.objects.all().order_by("-created_at")
    questions = Question.objects.select_related('author').prefetch_related('answers').all() 

    right_side_questions = Question.objects.select_related('author').prefetch_related('answers').order_by('-created_at').all()

    


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
  

    paginator = Paginator(questions, 5) 
    page_number = request.GET.get('page')
    questions = paginator.get_page(page_number)

    context = {
        "blogs":blogs,
        "questions" :questions,

        "right_side_questions":right_side_questions
    
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

    
        if title or content:
            Question.objects.create(
                author=request.user,
                title=title,
                content=content,
                image=image
            )
            return redirect('questions_list')
    return redirect('questions_list')


def popular_question(request):
    
    
    blogs = BlogPost.objects.all().order_by("-created_at")

    right_side_questions = Question.objects.select_related('author').prefetch_related('answers').order_by('-created_at').all()

    
    popular_question = Question.objects.annotate(
        num_answers=Count('answers')
    ).order_by('-num_answers', '-created_at')   
    

    query = request.GET.get('q')
    if query:
        popular_question = popular_question.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )



    paginator = Paginator(popular_question, 5) 
    page_number = request.GET.get('page')
    popular_question = paginator.get_page(page_number)

    context = {
        "blogs":blogs,
        "popular_question" :popular_question,

        "right_side_questions":right_side_questions
    
    }

    return render(request, 'forum/popular_question.html', context)



def forum_all_user_list(request):

    all_users = CustomUserModel.objects.prefetch_related('authored_posts','questions').order_by('created_at').all()

    paginator = Paginator(all_users, 8)
    page_number = request.GET.get('page')
    all_users = paginator.get_page(page_number)

    context = {
        'all_users': all_users
    }
    
    return render(request, "forum/forum_user.html", context)



def forum_user_profile_details(request, pk):


    user_profile = get_object_or_404(CustomUserModel, pk=pk)


    all_blogs = BlogPost.objects.filter(author=user_profile).order_by("-created_at")
    all_questions = user_profile.questions.all().order_by("-created_at")



    user_blogs = BlogPost.objects.filter(author=user_profile).order_by("-created_at")
    user_questions = user_profile.questions.all().order_by("-created_at")

    # paginator for blogs
    paginator = Paginator(user_blogs, 4)
    page_number = request.GET.get('page')
    user_blogs = paginator.get_page(page_number)


    # paginator for question
    paginator = Paginator(user_questions, 4)
    page_number = request.GET.get('page')
    user_questions = paginator.get_page(page_number)


    context = {
        'user_blogs': user_blogs,
        'user_questions' : user_questions,
        'user_profile':user_profile,
        'all_blogs':all_blogs,
        'all_questions':all_questions

    }

    return render(request, "forum/forum_user_profile.html", context)