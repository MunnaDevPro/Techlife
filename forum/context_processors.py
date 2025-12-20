from django.shortcuts import render , redirect , get_object_or_404
from django.db.models import Count
from forum.models import Question

def popular_questions(request):
    popular_question = Question.objects.annotate(
        num_answers=Count('answers')
    ).order_by('-num_answers', '-created_at')   
    
    context = {
        "popular_question": popular_question,
    }
    return(context) 

