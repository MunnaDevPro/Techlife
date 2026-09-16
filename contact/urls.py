from django.urls import path
from .views import contact_or_support_view

urlpatterns = [
    path('submit/', contact_or_support_view, name='contact_or_support'),
]
