from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

def staff_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, "You must be a staff member to access the dashboard.")
            return redirect(f"{reverse('login')}?next={request.path}")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
