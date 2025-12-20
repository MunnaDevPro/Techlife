from django.urls import path
from forum.views import forum_user_profile_details ,forum_all_user_list, popular_question, questions_list, questions, post_answer, create_question


urlpatterns = [
    path("all_question/",questions_list, name="questions_list"),
    path("questions/<slug:slug>/",questions, name="questions"),
    path("question/<slug:slug>/answer/",post_answer,name="post_answer"),

    path("ask-question/",create_question, name="create_question"),

    path("popular-question/",popular_question, name="popular_question"),

    path("forum-users/",forum_all_user_list, name="forum_all_user_list"),

    path("profile/<int:pk>/",forum_user_profile_details, name="forum_user_profile_details")


]