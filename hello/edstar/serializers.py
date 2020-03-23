from rest_framework import serializers
from .models import Enrollment, Activity, UserEvaluation


class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = '__all__'


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = '__all__'


class UserEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserEvaluation
        fields = '__all__'
