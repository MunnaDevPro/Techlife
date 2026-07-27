from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.db.models import Count
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from dashboard.permissions import staff_required
from dashboard.views.views import get_dashboard_context
from forum.models import Question, Answer
from dashboard.models import ModerationLog

@staff_required
def question_list(request):
    """List forum questions with answer counts."""
    # Annotate answer counts and prefetch author
    questions = Question.objects.select_related('author').annotate(answer_count=Count('answers')).order_by('-created_at')
    
    ctx = get_dashboard_context(request, "Forum Questions", "Forum", "dashboard:forum_questions")
    ctx.update({
        "questions": questions,
    })
    return render(request, "dashboard/forum/question_list.html", ctx)

@staff_required
@require_POST
@ratelimit(key='user', rate='30/m', block=True)
def question_delete(request, pk):
    """Delete a forum question after verification of delete permission."""
    question = get_object_or_404(Question, pk=pk)
    
    # Guardian object-level or model-level permission checks
    if not (request.user.is_superuser or request.user.has_perm('forum.delete_question', question) or request.user.has_perm('forum.delete_question')):
        raise PermissionDenied("You do not have permission to delete this question.")
        
    answer_count = question.answers.count()
    question.delete()
    
    # Audit log
    ModerationLog.objects.create(
        moderator=request.user,
        action='remove',
        details=f"Deleted question ID {pk} ('{question.title}') which cascaded and deleted {answer_count} answers."
    )
    
    messages.success(request, f"Question deleted successfully along with its {answer_count} answers.")
    return redirect("dashboard:forum_questions")

@staff_required
def answer_list(request):
    """List forum answers."""
    answers = Answer.objects.select_related('author', 'question').order_by('-created_at')
    
    ctx = get_dashboard_context(request, "Forum Answers", "Forum", "dashboard:forum_answers")
    ctx.update({
        "answers": answers,
    })
    return render(request, "dashboard/forum/answer_list.html", ctx)

@staff_required
@require_POST
@ratelimit(key='user', rate='30/m', block=True)
def answer_delete(request, pk):
    """Delete a forum answer."""
    answer = get_object_or_404(Answer, pk=pk)
    
    if not (request.user.is_superuser or request.user.has_perm('forum.delete_answer', answer) or request.user.has_perm('forum.delete_answer')):
        raise PermissionDenied("You do not have permission to delete this answer.")
        
    answer.delete()
    
    # Audit log
    ModerationLog.objects.create(
        moderator=request.user,
        action='remove',
        details=f"Deleted answer ID {pk} on question ID {answer.question_id}."
    )
    
    messages.success(request, "Answer deleted successfully.")
    return redirect("dashboard:forum_answers")
