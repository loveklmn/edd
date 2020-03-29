from django.urls import path, include
from rest_framework.authtoken import views as token_views
from .views import *

urlpatterns = [
    path('register/', GetOrCreateUserAPI.as_view()),
    path('enrollment/', ManagerEnrollmentAPI.as_view()),
    path('interview/', InterviewAPI.as_view()),
    path('activity/', ActivityAPI.as_view()),
    path('user/', ManageUserApi.as_view()),
    path('manager/', ManageSuperUserApi.as_view()),
    path('interview/', InterviewAPI.as_view()),
    path('enrollments/', UserEnrollmentAPI.as_view()),
    path('section/', SectionAPI.as_view()),
    path('course/', MangageCourseAPI.as_view()),
    path('lesson/', LessonAPI.as_view())
]
