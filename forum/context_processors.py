from django.db.models import Count
from forum.models import Question,Follow_section

def popular_questions(request):
    popular_question = Question.objects.annotate(
        num_answers=Count('answers')
    ).order_by('-num_answers', '-created_at')   
    
    context = {
        "popular_question": popular_question,
    }
    return(context) 




def global_follow_list(request):
    if request.user.is_authenticated:
        follow_obj, _ = Follow_section.objects.get_or_create(user=request.user)
        
        return {
            'global_followers': [f.user for f in request.user.followers.all()],
            'global_following': follow_obj.following.all(),
        }
    return {
        'global_followers': [],
        'global_following': [],
    }
