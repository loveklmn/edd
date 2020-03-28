from rest_framework import serializers
from .models import *


class UserMetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMeta
        fields = '__all__'


class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = '__all__'


class UserEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ['id', 'name', 'pictureUrl']


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = '__all__'


class UserEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserEvaluation
        fields = '__all__'


class UserEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserEnrollment
        fields = '__all__'


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = '__all__'


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'
        ordering_fields = 'order'


class UserActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivity
        fields = '__all__'
