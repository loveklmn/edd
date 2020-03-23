from django.urls import path, include
from rest_framework.authtoken import views as token_views
from .views import CreateUserAPI, EnrollmentAPI, InterviewAPI, ActivityAPI, TestApi

urlpatterns = [
    path('register/', CreateUserAPI.as_view()),
    path('enrollment/', EnrollmentAPI.as_view()),
    path('interview/', InterviewAPI.as_view()),
    path('activity/', ActivityAPI.as_view()),
]
