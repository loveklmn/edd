from django.shortcuts import render
from rest_framework.views import APIView, Response
from django.http import JsonResponse

from django.contrib.auth.models import User
from rest_framework import status

from rest_framework.exceptions import NotFound, PermissionDenied, ParseError
from rest_framework.authtoken.models import Token

import datetime

from .models import UserMeta, UserEvaluation
from .serializers import *

import json

from django.conf import settings


def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


def bit_to_num(bit):
    '''将处于bit二进制位上的数转为十进制'''
    return 1 << (bit-1)


def has_authority(user, string):
    '''
    user = request.user
    1 管理招生信息 manage_enrollment
    2 管理面试信息 manage_interview
    3 参与面试评价 participate_interview
    4 管理课程 manage_lessons
    5 管理活动 manage_activity
    6 管理校友 manage_fellow
    7 设置管理员 set_admin
    8 是否是管理员 is_admin
    '''
    right_dict = {
        'manage_enrollment':     1,
        'manage_interview':      2,
        'participate_interview': 3,
        'manage_lessons':        4,
        'manage_activity':       5,
        'manage_fellow':         6,
        'set_admin':             7,
        'is_admin':              8
    }
    right = num_to_bit(user.privilege)
    return right_dict[string] in right


def num_to_bit(num):
    '''输出将十进制num转二进制后为1的位数'''
    bit_array = []
    for i in range(32):
        if num % 2:
            bit_array.append(i+1)
        num = num >> 1
    return bit_array


def get_or_raise(data, attr):
    '''获取字典data的attr属性，否则抛出异常'''
    if data.get(attr):
        return data[attr]
    else:
        raise ParseError('Attr "{}" cannot be empty.'.format(attr))


def get_user(**kwargs):
    '''
    require: user=request.user or
    '''
    usermeta_query = UserMeta.objects.filter(**kwargs)
    if not usermeta_query.exists():
        raise NotFound('User({}) not found.'.format(kwargs))
    user = usermeta_query[0]
    return user


class CreateUserAPI(APIView):
    def _create_user(self, unionID):
        user = User.objects.create_user(username=unionID, password=unionID)
        user.save()
        return user

    def get(self, request):
        postdata = request.data
        unionID = get_or_raise(postdata, 'unionID')
        user_query = User.objects.filter(username=unionID)
        if not user_query.exists():
            raise NotFound('No such user.')
        user = user_query[0]
        token = Token.objects.get_or_create(user=user)[0]
        return JsonResponse({'token': token.key}, status=200)

    def post(self, request):
        postdata = request.data
        unionID = get_or_raise(postdata, 'unionID')
        avatar_url = get_or_raise(postdata, 'avatarUrl')
        nick_name = get_or_raise(postdata, 'nickName')
        gender = get_or_raise(postdata, 'gender')
        phone = get_or_raise(postdata, 'phone')
        birth_date = get_or_raise(postdata, 'birthDate')
        wechat = get_or_raise(postdata, 'wechat')
        mail = get_or_raise(postdata, 'mail')
        country = get_or_raise(postdata, 'country')
        province = get_or_raise(postdata, 'province')
        city = get_or_raise(postdata, 'city')
        kind = get_or_raise(postdata, 'kind')
        privilege = int(postdata.get('privilege', 0))
        sub_field = postdata.get('sub_field', '')
        user = self._create_user(unionID)
        new_user = UserMeta.objects.create(
            user=user, unionID=unionID, avatar_url=avatar_url,
            nick_name=nick_name, gender=gender, phone=phone,
            birth_date=birth_date, wechat=wechat, mail=mail,
            country=country, province=province, city=city,
            kind=kind, privilege=privilege, sub_field=sub_field,
        )
        return Response(status=status.HTTP_200_OK)


class EnrollmentAPI(APIView):
    def get(self, request):
        enrollments = Enrollment.objects.all()
        return Response(EnrollmentSerializer(enrollments).data, status=status.HTTP_200_OK)

    def post(self, request):
        postdata = request.data
        id = get_or_raise(postdata, 'id')
        name = postdata.get('name')
        description = postdata.get('description')
        open_status = postdata.get('openStatus', False)
        time = postdata.get('endAt').split('-')
        end_at = datetime.datetime(
            time.get(0), time.get(1), time.get(2),
            time.get(3), time.get(4), time.get(5)
        )
        if id == -1:
            enrollment = Enrollment.object.create(
                name=name,
                description=description,
                open_status=open_status,
                end_at=end_at)
            return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)
        else:
            enrollment_query = Enrollment.objects.filter(id=id)
            if not enrollment_query.exists():
                raise NotFound('Enrollment not found.')
            enrollment = enrollment_query[0]
            if name:
                enrollment.name = name
            if description:
                enrollment.description = description
            if open_status:
                enrollment.open_status = open_status
            if end_at:
                enrollment.end_at = end_at
            enrollment.save()
        return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_200_OK)


class ActivityAPI(APIView):
    def get(self, request):
        activity = Activity.objects.all()
        serializer = ActivitySerializer(activity).data
        return Response(serializer, status=status.HTTP_200_OK)

    def post(self, request):
        postdata = request.data
        id = get_or_raise(postdata, 'id')
        activity_query = Activity.objects.filter(id=id)
        if not activity_query.exists():
            raise NotFound('Activity not found.')
        activity = activity_query[0]

        name = postdata.get('name')
        description = postdata.get('description')
        if name:
            activity.name = name
        if description:
            activity.description = description
        activity.save()
        return Response(ActivitySerializer(activity).data, status=status.HTTP_201_CREATED)


class InterviewAPI(APIView):
    def get(self, request):
        user_query = UserMeta.objects.filter(user=request.user)
        if not user_query.exists():
            raise PermissionDenied()
        user = user_query[0]
        if has_authority(user, 'manage_interview'):
            '''get all interviews'''
            interviews = UserEvaluation.objects.all()
            return Response(UserEvaluationSerializer(interviews).data, status=status.HTTP_200_OK)
        elif has_authority(user, 'participate_interview'):
            '''get his/her interviews'''
            interviews_query = UserEvaluation.objects.filter(
                interviewer=user)
            if not interviews_query.exists():
                raise NotFound('No interviews.')
            interviews = interviews_query
            return Response(UserEvaluationSerializer(interviews).data, status=status.HTTP_200_OK)
        else:
            raise PermissionDenied

    def post(self, request):
        postdata = request.data
        id = int(get_or_raise(postdata, 'id'))
        if id == -1:
            interviewer = get_or_raise(postdata, 'interviewer')
            interviewee = get_or_raise(postdata, 'interviewee')
            score = postdata.get('score', 0)
            review = postdata.get('review', '')
            interviewer_id = int(interviewer)
            interviewee_id = int(interviewee)
            interviewer = UserMeta.objects.get(id=interviewer_id)
            interviewee = UserMeta.objects.get(id=interviewee_id)
            interview = UserEvaluation.objects.create(
                interviewer=interviewer,
                interviewee=interviewee,
                score=score,
                review=review
            )
            return Response(UserEvaluationSerializer(interview).data, status=status.HTTP_200_OK)
        else:
            interview_query = UserEvaluation.objects.filter(id=id)
            if not interview_query.exists():
                raise NotFound('Interview not found.')
            interview = interview_query[0]
            interviewer = postdata.get('interviewer')
            interviewee = postdata.get('interviewee')
            score = postdata.get('score')
            review = postdata.get('review')
            if interviewer:
                interview.interviewer = interviewer
            if interviewee:
                interview.interviewee = interviewee
            if score:
                interview.score = score
            if review:
                interview.review = review
            interview.save()
        return Response(UserEvaluationSerializer(interview).data, status=status.HTTP_201_CREATED)
