from django.shortcuts import render
from rest_framework.views import APIView, Response
from django.http import JsonResponse

from django.contrib.auth.models import User
from rest_framework import status

from rest_framework.exceptions import NotFound, PermissionDenied, ParseError
from rest_framework.authtoken.models import Token

import datetime

from .models import *
from .serializers import *

import json

from django.conf import settings

from dateutil import parser as date_parser

from .wechat import get_open_id


def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


def bit_to_num(bit):
    '''将处于bit二进制位上的数转为十进制'''
    return 1 << (bit-1)


def is_manager_required(func):
    '''
    只能装饰APIView类post或get成员函数
    '''
    def warpper(*args, **kwargs):
        request = args[1]
        user = get_user(user=request.user)
        if user.privilege > 0:
            return func(*args, **kwargs)
        raise PermissionDenied()
    return warpper


def privilege_required(privilege, option='and'):
    '''
    只能装饰APIView类post或get成员函数
    '''
    def middle(func):
        def warpper(*args, **kwargs):
            request = args[1]
            user = UserMeta.objects.filter(user=request.user).first()
            if type(privilege) == str:
                if privilege == 'is_manager' and user.privilege > 0:
                    return func(*args, **kwargs)
                else:
                    return has_authority(user, privilege)
            elif type(privilege) == list:
                passed = ''
                if option == 'or':
                    passed = False
                elif option == 'and':
                    passed = True
                for each_privilege in privilege:
                    if has_authority(user, privilege):
                        if option == 'or':
                            passed = True
                        elif option == 'and':
                            passed = False
                if passed:
                    return func(*args, **kwargs)
            else:
                raise PermissionDenied()
        return warpper
    return middle


def has_authority(user, string):
    '''
    user = UserMeta
    1 管理招生信息 can_manage_enrollment
    2 管理面试信息 can_manage_interview
    3 参与面试评价 can_participate_interview
    4 管理课程 can_manage_lessons
    5 管理活动 can_manage_activity
    6 管理校友 can_manage_fellow
    7 设置管理员 can_set_manager
    8 是否是管理员 can_is_amanager
    '''
    right_dict = {
        'can_manage_enrollment':     1,
        'can_manage_interview':      2,
        'can_participate_interview': 3,
        'can_manage_lessons':        4,
        'can_manage_activity':       5,
        'can_manage_fellow':         6,
        'can_set_manager':           7
    }
    return right_dict[string] in num_to_bit(user.privilege)


def num_to_bit(num):
    '''输出将十进制num转二进制后为1的位数'''
    bit_array = []
    for i in range(32):
        if num % 2:
            bit_array.append(i+1)
        num = num >> 1
    return bit_array


def get_or_raise(data, attr, attr_type=None):
    '''获取字典data的attr属性，否则抛出异常'''
    value = data.get(attr)
    if value:
        if not attr_type:
            return attr
        elif type(value) == attr_type:
            return value
        else:
            raise ParseError('Attribute "{}" type wrong.'.format(attr))
    else:
        raise ParseError('Attribute "{}" cannot be empty.'.format(attr))


def save_or_raise(serializer):
    if serializer.is_valid():
        serializer.save()
    else:
        print(serializer.errors)
        raise ParseError(serializer.errors)


def get_user(**kwargs):
    '''
    require: user=request.user or id= int
    '''
    return UserMeta.objects.filter(**kwargs).first()


'''
GET 获取
POST 创建or修改
DELETE 删除
'''


class CreateUserAPI(APIView):
    def _create_user(self, openId):
        user = User.objects.create_user(username=openId, password=openId)
        user.save()
        return user

    def get(self, request):
        postdata = request.data
        code = get_or_raise(postdata, 'code', str)
        openId = get_open_id(code)
        user = get_user(openId=openId)
        token = Token.objects.get_or_create(user=user)[0]
        return JsonResponse({'data': UserMetaSerializer(user).data,
                             'token': token.key}, status=status.HTTP_200_OK)

    def post(self, request):
        postdata = request.data
        openId = get_or_raise(postdata, 'openId')
        user = self._create_user(openId)
        serializer = UserMetaSerializer(
            data=get_or_raise(postdata, 'userInfo', dict))
        save_or_raise(serializer)
        return Response(status=status.HTTP_200_OK)


class EnrollmentAPI(APIView):
    # @privilege_required('can_manage_enrollment')
    def get(self, request):
        '''交互1 查看招生列表'''
        enrollments = Enrollment.objects.all()
        enrollments = list(enrollments)
        for enrollment in enrollments:
            enrollment.count = UserEnrollment.objects.filter(
                enrollment=enrollment, status='AC').count()
        return Response(EnrollmentSerializer(enrollments, many=True).data, status=status.HTTP_200_OK)

    # @privilege_required('can_manage_enrollment')
    def post(self, request):
        postdata = request.data
        enrollmentId = postdata.get('enrollmentId')
        name = postdata.get('name')
        description = postdata.get('description')
        open_status = postdata.get('openStatus')
        time = get_or_raise(postdata, 'endAt', str)
        end_at = date_parser.parse(time)
        if not enrollmentId:
            '''交互2 创建招生管理资料'''
            serializer = EnrollmentSerializer(data={
                'name': name,
                'description': description,
                'open_status': open_status,
                'end_at': end_at
            })
            save_or_raise(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        else:
            '''交互2 编辑招生管理资料'''
            enrollment = Enrollment.objects.filter(
                id=enrollmentId).first()
            serializer = EnrollmentSerializer(instance=enrollment, data={
                'name': name,
                'description': description,
                'open_status': open_status,
                'end_at': end_at
            })
            save_or_raise(serializer)
            return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_200_OK)

    # @privilege_required('can_manage_enrollment')
    def delete(self, request):
        postdata = request.data
        enrollment_ids = get_or_raise(postdata, 'enrollmentId', list)
        return Response(enrollment_ids, status=status.HTTP_200_OK)
        for enrollment_id in enrollment_ids:
            Enrollment.objects.filter(
                id=enrollment_id).first().delete()
        return Response(status=status.HTTP_200_OK)


class ActivityAPI(APIView):
    def get(self, request):
        '''交互1 查看所有活动'''
        activity = Activity.objects.all()
        return Response(ActivitySerializer(activity, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        postdata = request.data
        activity_id = get_or_raise(postdata, 'activityId')
        enrollment_id = get_or_raise(postdata, 'enrollment', int)
        enrollment = Enrollment.objects.filter(
            id=enrollment_id).first()
        name = get_or_raise(postdata, 'name', str)
        description = get_or_raise(postdata, 'description', str)

        if not activity_id:
            '''交互2 创建活动'''
            serializer = ActivitySerializer(data={
                'enrollment': enrollment,
                'name': name,
                'description': description
            })
            save_or_raise(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            '''交互3 修改活动'''
            activity = Activity.objects.filter(
                id=activity_id).first()
            serializer = ActivitySerializer(instance=activity, data={
                                            'name': name, 'description': description})
            save_or_raise(serializer)
            return Response(status=status.HTTP_200_OK)


class ManageUserApi(APIView):
    def get(self, request):
        '''交互0 查看所有用户'''
        user = UserMeta.objects.all()
        return Response(UserMetaSerializer(user, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        '''交互2 编辑用户字段 '''
        postdata = request.data
        user = get_user(id=get_or_raise(postdata, 'userId', int))
        serializer = UserMetaSerializer(
            instance=user, data=postdata.get('userInfo'), partial=True)

    def delete(self, request):
        '''交互1 删除用户'''
        postdata = request.data
        user_id = get_or_raise(postdata, 'userId', int)
        UserMeta.objects.filter(id=user_id).first().delete()
        return Response(status=status.HTTP_200_OK)


class ManageSuperUserApi(APIView):
    def get(self, request):
        '''交互0 获得所有管理员'''
        user = UserMeta.objects.exclude(privilege=0)
        return Response(UserMetaSerializer(user, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        postdata = request.data
        bit = postdata.get('bit')
        if bit:
            '''交互1 修改权限'''
            user = get_user(id=get_or_raise(postdata, 'userId', int))
            privilege = 1 << (bit - 1)
            serializer = UserMetaSerializer(instance=user, data={
                privilege: user.privilege + privilege
            }, partial=True)
            save_or_raise(serializer)
            return Response(status=status.HTTP_200_OK)
        else:
            '''交互2 增加管理员√'''
            managers = get_or_raise(postdata, 'managers', list)
            for manager in managers:
                user_id = get_or_raise(manager, 'userId', int)
                privilege = 1 << (get_or_raise(manager, 'bit', int) - 1)
                get_user(id=user_id).privilege + privilege
            return Response(status=status.HTTP_200_OK)

    def delete(self, request):
        '''交互3 删除管理员'''
        postdata = request.data
        user_ids = get_or_raise(postdata, 'userId', list)
        for user_id in user_ids:
            get_user(id=user_id).delete()
        return Response(status=status.HTTP_200_OK)


class InterviewAPI(APIView):
    # @privilege_required(['can_manage_enrollment', 'can_participate_interview'], 'or')
    def get(self, request):
        '''交互1 查看面试管理(有面试管理权+有参与面试评价权)'''
        user = UserMeta.objects.filter(user=request.user).first()
        if has_authority(user, 'can_manage_interview'):
            interviews = UserEnrollment.objects.all()
            return Response(UserEnrollmentSerializer(interviews, many=True).data, status=status.HTTP_200_OK)
        elif has_authority(user, 'can_participate_interview'):
            interviews = UserEvaluation.objects.filter(interviewer=user)
            return Response(UserEvaluationSerializer(interviews, many=True).data, status=status.HTTP_200_OK)
        else:
            raise PermissionDenied

    # @privilege_required('can_manage_interview')
    def post(self, request):
        '''交互2 给已有报名信息分配面试官(有面试管理权)'''
        postdata = request.data

        user_enroll_id = get_or_raise(postdata, 'userEnrollId', int)
        user_enroll = UserEnrollment.objects.filter(id=user_enroll_id).first()

        interviewee_id = get_or_raise(postdata, 'interviewee', int)
        interviewee = get_user(id=interviewee_id)

        interviewer_ids = get_or_raise(postdata, 'interviewer', list)

        serializer = UserMetaSerializer(
            instance=interview, data=postdata.get('user'))
        save_or_raise(serializer)  # 更改用户资料

        serializer = UserEnrollmentSerializer(
            instance=interview,
            data={'status': get_or_raise(postdata, 'status', str)},
            partial=True)
        save_or_raise(serializer)  # 更改用户注册课的状态

        for interviewer_id in interviewer_ids:
            serializer = UserEvaluationSerializer(data={
                'interviewer': get_user(id=interviewer_id),
                'interviewee': get_user(id=interviewee_id),
            }, partial=True)
            save_or_raise(serializer)  # 添加面试
        return Response(status=status.HTTP_201_CREATED)

    # @privilege_required('can_participate_interview')
    def put(self, request):
        ''' 交互3 评价面试(有参与面试评价权)'''
        postdata = request.data
        interview_id = postdata.get('interviewId')
        user = get_user(user=request.user)
        interview = UserEvaluation.objects.filter(id=interview_id).first()
        interviewer = get_or_raise(postdata, 'interviewer', int)
        interviewee_id = get_or_raise(postdata, 'interviewee', int)
        score = postdata.get('score')
        review = postdata.get('review')
        serializer = UserEvaluationSerializer(instance=interview, data={
            'score': score,
            'review': review
        }, partial=True)
        save_or_raise(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # @privilege_required('can_manage_interview')
    def delete(self, request):
        postdata = request.data
        interview_id = postdata.get('interviewId', int)
        UserEvaluation.objects.filter(id=interview_id).first().delete()
        return Response(status=status.HTTP_200_OK)


class UserEnrollmentAPI(APIView):
    def get(self, request):
        user_enroll = UserEnrollment.objects.all()
        return Response(UserEnrollmentSerializer(user_enroll, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        postdata = request.data
        user_id = get_or_raise(postdata, 'user', int)
        enrollment_id = get_or_raise(postdata, 'enrollment', int)
        status = postdata.get('status')
        user = get_user(user=request.user)
        enrollment = Enrollment.objects.filter(id=enrollment_id).first()
        serializer = UserEnrollmentSerializer(instance=enrollment, data={
            user: user,
            enrollment: enrollment,
            status: status
        })
        save_or_raise(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MangageCourseAPI(APIView):
    # @privilege_required('can_manage_course')
    def get(self, request):

        postdata = request.query_params
        course_id = postdata.get('courseId')
        if not course_id:
            '''交互1 查看所有的course'''
            courses = [{'enrollment': course.enrollment.name,
                        'name': course.name,
                        'description': course.description} for course in Course.objects.all()]
            return Response(courses, status=status.HTTP_200_OK)
        else:
            '''course的详细'''
            course = Course.objects.filter(id=course_id).first()
            sections = Section.objects.filter(course=course)
            data = []
            for section in sections:
                lessons = Lesson.objects.filter(
                    section=section).order_by('order')
                data.append({'name': section.name,
                             'lessons': LessonSerializer(lessons, many=True).data
                             })
            return Response(data, status=status.HTTP_200_OK)

    # @privilege_required('can_manage_course')
    def post(self, request):

        postdata = request.data
        course_id = postdata.get('courseId')
        enrollment_id = postdata.get('enrollmentId')
        name = postdata.get('name')
        description = postdata.get('description')

        course_id = postdata.get('courseId')
        if course_id:
            '''交互3 修改course'''
            course = Course.objects.filter(id=course_id).first()
            serializer = CourseSerializer(instance=course, data={
                'name': name,
                'description': description
            }, partial=True)
            save_or_raise(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            '''交互2 添加course'''
            serializer = CourseSerializer(data={
                'enrollment': enrollment_id,
                'name': name,
                'description': description
            })
            save_or_raise(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        '''交互4 删除course'''
        postdata = request.data
        course_ids = get_or_raise(postdata, 'courseId', list)
        for course_id in course_ids:
            Course.objects.filter(id=course_id).delete()
        return Response(status=status.HTTP_200_OK)


class SectionAPI(APIView):
    def get(self, request):
        postdata = request.query_params
        course_id = get_or_raise(postdata, 'courseId')
        course = Course.objects.filter(id=course_id).first()
        section = Section.objects.filter(course=course)
        return Response(SectionSerializer(section).data, status=status.HTTP_200_OK)

    def post(self, request):
        postdata = request.data
        course_id = postdata.get('courseId')
        name = postdata.get('name')
        course = Course.objects.filter(id=course_id).first()
        section = Section.objects.filter(course=course).first()
        serializer = SectionSerializer(instance=section, data={
            'name': name
        })
        save_or_raise(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LessonAPI(APIView):
    def get(self, request):
        postdata = request.query_params
        section_id = get_or_raise('sectionId')
        section = Section.objects.filter(id=section_id).first()
        lessons = Lesson.objects.filter(section=section)
        return Response(LessonSerializer(lessons).data, status=status.HTTP_200_OK)

    def post(self, request):
        postdata = request.data
        return Response(status=status.HTTP_200_OK)
