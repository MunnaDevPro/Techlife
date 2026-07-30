from django.shortcuts import redirect
from django.urls import reverse
from django.db.models import F
from dashboard.models import NotFoundLog

class Redirect404Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 404:
            path = request.path
            referer = request.META.get('HTTP_REFERER', '')[:1024]
            
            try:
                log, created = NotFoundLog.objects.get_or_create(
                    path=path,
                    defaults={'referer': referer, 'hit_count': 1}
                )
                if not created:
                    log.hit_count = F('hit_count') + 1
                    log.referer = referer
                    log.save(update_fields=['hit_count', 'referer', 'last_seen'])
            except Exception:
                pass
        return response