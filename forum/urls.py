from django.urls import path
from forum.views import questions_list, questions


urlpatterns = [
    path("all_question/",questions_list, name="questions_list"),
    path("questions/<slug:slug>/",questions, name="questions")

]