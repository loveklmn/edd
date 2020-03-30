from rest_framework import serializers
from .models import *


class UserMetaSerializer(serializers.ModelSerializer):
    field = serializers.DictField()

    class Meta:
        model = UserMeta
        read_only_fields = (
            'field',
        )
        exclude = ('is_deleted', 'deleted_at', 'openId', 'user')


class EnrollmentSerializer(serializers.ModelSerializer):
    people_count = serializers.IntegerField()

    class Meta:
        model = Enrollment
        exclude = ('is_deleted', 'deleted_at')
        read_only_fields = ('people_count',)
        ordering_fields = 'created_at'


class UserEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ['id', 'name', 'pictureUrl']


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        exclude = ('is_deleted', 'deleted_at')


class UserEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserEvaluation
        exclude = ('is_deleted', 'deleted_at')
        depth = 3


class UserEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserEnrollment
        exclude = ('is_deleted', 'deleted_at')


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        exclude = ('is_deleted', 'deleted_at')


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        exclude = ('is_deleted', 'deleted_at')


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        exclude = ('is_deleted', 'deleted_at')
        ordering_fields = 'order'


class UserActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivity
        exclude = ('is_deleted', 'deleted_at')
