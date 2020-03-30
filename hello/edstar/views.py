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
    6 管理校友 can_manage_alumni
    7 设置管理员 can_set_manager
    8 是否是管理员 can_is_amanager
    '''
    right_dict = {
        'can_manage_enrollment':     1,
        'can_manage_interview':      2,
        'can_participate_interview': 3,
        'can_manage_lessons':        4,
        'can_manage_activity':       5,
        'can_manage_alumni':         6,
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


class GetOrCreateUserAPI(APIView):
    ''' 小程序
    页面1 注册
    '''

    def _create_user(self, open_id):
        user = User.objects.create_user(username=open_id, password=open_id)
        user.save()
        return user

    def get(self, request):
        '''
        交互1 用户注册
        @params  String code wx.login()的code
        @returns String data 用户数据
        @returns String token 用户的token
        '''
        postdata = request.query_params
        code = get_or_raise(postdata, 'code', str)
        open_id = get_open_id(code)
        user_query = UserMeta.objects.filter(open_id=open_id)
        if user_query.exists:
            user = user_query.first()
        else:
            user = self._create_user(open_id)
        token = Token.objects.get_or_create(user=user)[0]
        return Response({'data': UserMetaSerializer(user).data,
                         'token': token.key}, status=status.HTTP_200_OK)


class UserEnrollmentAPI(APIView):
    ''' 小程序
    页面2 招生页
    页面3.1 招生详细页
    '''

    def get(self, request):
        '''
        情况1:      获得所有enrollment的信息
        @parameter Integer              enrollment_id    对应enrollment的ID     
        @returns   []                   enrollment      对应enrollment的信息
        @returns   ('RG'| 'RE' | ...)   status          当前用户对应所有enrollment的状态

        情况2:      获得所有enrollment
        @returns   [objects]            
        objects  - enrollment 所有enrollment的信息
        objects  - enrollment 对应enrollment的状态
        '''
        postdata = request.query_params
        enrollment_id = postdata.get('enrollment_id')
        user = get_user(user=request.user)
        if enrollment_id:
            enrollment = Enrollment.objects.filter(id=enrollment_id).first()
            user_enroll_query = UserEnrollment.objects.filter(
                user=user, enrollment=enrollment)
            if not user_enroll_query.exists:
                user_enroll_status = 'EM'
            else:
                user_enroll_status = user_enroll_query.first().status
            return Response({
                'enrollment': EnrollmentSerializer(enrollment).data,
                'status': user_enroll_status
            }, status=status.HTTP_200_OK)
        else:
            enrollments = Enrollment.objects.all()
            enrollment_data = []
            for enrollment in enrollments:
                user_enroll = UserEnrollment.objects.filter(
                    enrollment=enrollment, user=user).first()
                enrollment_data.append({
                    'enrollment': EnrollmentSerializer(enrollment).data,
                    'status': user_enroll.status
                })
            return Response(enrollment, status=status.HTTP_200_OK)

    def post(self, request):
        ''' 小程序  填写enrollment的报名信息
        @params  {}     subField    用户信息
        @params  String province    用户的省
        @returns {}     userInfo    用户信息
        '''
        postdata = request.data
        user = get_user(user=request.user)
        subField = postdata.get('subField')
        province = postdata.get('province')
        enrollment_id = postdata.get('enrollment_id')
        serializer = UserMetaSerializer(instance=user, data={
            'subField': subField,
            'province': province
        }, partial=True)
        save_or_raise(serializer)
        enrollment = Enrollment.objects.filter(id=enrollment_id).first()
        UserEnrollment.objects.filter(
            enrollment=enrollment, user=user).first().status = 'REG'
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ManagerEnrollmentAPI(APIView):
    def get(self, request):
        '''交互1 查看招生列表'''
        enrollments = Enrollment.objects.all()
        # enrollments = list(enrollments)
        # for enrollment in enrollments:
        #     enrollment.count = UserEnrollment.objects.filter(
        #         enrollment=enrollment, status='AC').count()
        return Response({'data': EnrollmentSerializer(enrollments, many=True).data}, status=status.HTTP_200_OK)

    # @privilege_required('can_manage_enrollment')
    def post(self, request):
        postdata = request.data
        enrollment_id = postdata.get('enrollment_id')
        name = postdata.get('name')
        picture_url = postdata.get('picture_url')
        description = postdata.get('description')
        open_status = postdata.get('open_status')
        time = postdata.get('end_at')
        end_at = date_parser.parse(time)
        if not enrollment_id:
            '''交互2 创建招生管理资料'''
            serializer = EnrollmentSerializer(data={
                'name': name,
                'description': description,
                'pictureUrl': picture_url,
                'open_status': open_status,
                'end_at': end_at
            })
            save_or_raise(serializer)
            return Response({'data': serializer.data}, status=status.HTTP_201_CREATED)

        else:
            '''交互2 编辑招生管理资料'''
            enrollment = Enrollment.objects.filter(
                id=enrollment_id).first()
            serializer = EnrollmentSerializer(instance=enrollment, data={
                'name': name,
                'description': description,
                'open_status': open_status,
                'pictureUrl': picture_url,
                'end_at': end_at
            })
            save_or_raise(serializer)
            return Response({'data': serializer.data}, status=status.HTTP_200_OK)

    # @privilege_required('can_manage_enrollment')
    def delete(self, request):
        postdata = request.data
        enrollment_ids = get_or_raise(postdata, 'enrollment_id', list)
        for enrollment_id in enrollment_ids:
            Enrollment.objects.filter(
                id=enrollment_id).first().delete()
        return Response(status=status.HTTP_200_OK)


class ActivityAPI(APIView):
    ''' web | 小程序
    页面4.1 活动页
    '''

    def get(self, request):
        ''' 小程序
        交互1 查看所有活动
        交互2 点击对应活动, 获得活动详细
        '''
        postdata = request.query_params
        activity_id = postdata.get('activity_id')
        if activity_id:
            activity = Activity.objects.filter(id=activity_id).first()
            return Response(ActivitySerializer(activity).data, status=status.HTTP_200_OK)
        else:
            activity_data = [{
                'name': activity.name,
                'pictureUrl': activity.pictureUrl,
                'peopleCount': UserActivity.objects.filter(activity=activity, status=True).count()
            } for activity in Activity.objects.all()]
            return Response(activity_data, status=status.HTTP_200_OK)

    def post(self, request):
        '''web
        管理员新建活动和修改活动
        '''
        postdata = request.data
        activity_id = get_or_raise(postdata, 'activity_id')
        enrollment_id = get_or_raise(postdata, 'enrollment', int)
        enrollment = Enrollment.objects.filter(
            id=enrollment_id).first()
        name = get_or_raise(postdata, 'name', str)
        description = get_or_raise(postdata, 'description', str)
        limit = postdata.get('limit')
        if not activity_id:
            '''交互2 创建活动'''
            serializer = ActivitySerializer(data={
                'enrollment': enrollment,
                'name': name,
                'description': description,
                'limit': limit or 100,
                'end_at': postdata.get('endAt')
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

    def put(self, request):
        ''' 小程序 
        页面4.2 活动详细页
        交互3 报名活动
        '''
        postdata = request.data
        activity_id = get_or_raise(postdata, 'activity_id')
        activity = Activity.objects.filter(id=activity_id).first()
        if activity.limit >= UserActivity.objects.filter(activity=activity).count():
            return Response({'msg': '活动人数已满。'}, status=status.HTTP_400_BAD_REQUEST)
        if activity.end_at > timezone.now():
            return Response({'msg': '活动人数已关闭。'}, status=status.HTTP_400_BAD_REQUEST)
        user = get_user(user=request.user)
        user_activity_query = UserActivity.objects.filter(
            activity=activity, user=user)
        if user_activity_query:
            user_activity_query.first().status = True
        else:
            serializer = UserActivitySerializer(data={
                'user': user,
                'activity': activity,
                'status': True
            })
            save_or_raise(serializer)
        return Response(status=status.HTTP_200_OK)

    def delete(self, request):
        ''' 小程序 
        页面4.2 活动详细页
        交互3 退出活动
        '''
        postdata = request.data
        user = get_user(user=request.user)
        activity_id = get_or_raise(postdata, 'activity_id')
        activity = Activity.objects.filter(id=activity_id).first()
        UserActivity.objects.filter(
            activity=activity, user=user).first().status = False
        return Response(status=status.HTTP_200_OK)


class ManageUserApi(APIView):
    def get(self, request):
        '''交互0 查看所有用户'''
        user = UserMeta.objects.all()
        return Response(UserMetaSerializer(user, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        '''交互2 编辑用户字段 '''
        postdata = request.data
        user = get_user(id=get_or_raise(postdata, 'user_id', int))
        serializer = UserMetaSerializer(
            instance=user, data=postdata.get('userInfo'), partial=True)

    def delete(self, request):
        '''交互1 删除用户'''
        postdata = request.data
        user_id = get_or_raise(postdata, 'user_id', int)
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
            user = get_user(id=get_or_raise(postdata, 'user_id', int))
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
                user_id = get_or_raise(manager, 'user_id', int)
                privilege = 1 << (get_or_raise(manager, 'bit', int) - 1)
                get_user(id=user_id).privilege + privilege
            return Response(status=status.HTTP_200_OK)

    def delete(self, request):
        '''交互3 删除管理员'''
        postdata = request.data
        user_ids = get_or_raise(postdata, 'user_id', list)
        for user_id in user_ids:
            get_user(id=user_id).delete()
        return Response(status=status.HTTP_200_OK)


class InterviewAPI(APIView):
    ''' web
    页面2 面试管理(管理面试信息权限/参与面试评价权限)
    管理面试信息权限可以看到所有被面试者信息，并可以编辑他们的信息
    参与面试评价权限(交互3)只能看到被分配的面试者信息，不能编辑他们的信息，只能添加面试评价信息
    '''

    # @privilege_required(['can_manage_enrollment', 'can_participate_interview'], 'or')
    def get(self, request):
        '''交互1 查看面试管理(有面试管理权+有参与面试评价权)'''
        user = UserMeta.objects.filter(user=request.user).first()
        if has_authority(user, 'can_manage_interview'):
            postdata = request.query_params
            enrollment_id = postdata.get('enrollment_id')
            enrollment = Enrollment.objects.filter(id=enrollment_id).first()
            user_enrolls = UserEnrollment.objects.filter(
                enrollment=enrollment, status='REG')
            user_enroll_interview_data = []
            for user_enroll in user_enrolls:
                interviews = UserEvaluation.objects.filter(
                    enrollment=user_enroll.enrollment,
                    interviewee=user_enroll.user)
                user_enroll_interview_data.append({
                    'status': user_enroll.status,
                    'enrollment': EnrollmentSerializer(user_enroll.enrollment).data,
                    'user': UserMetaSerializer(user_enroll.user).data,
                    'interviews': UserEvaluationSerializer(interviews, many=True).data
                })
            return Response(user_enroll_interview_data, status=status.HTTP_200_OK)
        elif has_authority(user, 'can_participate_interview'):
            interviews = UserEvaluation.objects.filter(interviewer=user)
            interviews_data = [{
                'enrollment': EnrollmentSerializer(interview.enrollment).data,
                'interviewee': {
                    'province': interview.interviewee.province,
                    'subField': interview.interviewee.subField,
                },
                'score': interview.score,
                'review': interview.review,
            } for interview in interviews]
            return Response(interviews_data, status=status.HTTP_200_OK)
        else:
            raise PermissionDenied

    # @privilege_required('can_manage_interview')
    def post(self, request):
        '''交互2 给已有报名信息分配面试官(有面试管理权)'''
        postdata = request.data

        user_enroll_id = get_or_raise(postdata, 'userEnroll_id', int)
        user_enroll = UserEnrollment.objects.filter(id=user_enroll_id).first()

        interviewee_id = get_or_raise(postdata, 'interviewee', int)
        interviewee = get_user(id=interviewee_id)

        interviewer_ids = get_or_raise(postdata, 'interviewers', list)
        return_data = {}

        data = {}
        province = postdata.get('province')
        if province:
            data['province'] = province
        data['subField']: postdata.get('subField')
        serializer = UserMetaSerializer(
            instance=interviewee, data=data, partial=True)
        save_or_raise(serializer)
        return_data['user'] = serializer.data  # 更改用户资料
        user_status = get_or_raise(postdata, 'status', str)
        serializer = UserEnrollmentSerializer(
            instance=user_enroll,
            data={'status': user_status},
            partial=True)
        save_or_raise(serializer)
        if user_status == 'ACC':
            user_enroll.enrollment.people_count += 1
        return_data['userEnrollment'] = serializer.data  # 更改用户注册课的状态

        for interviewer_id in interviewer_ids:
            serializer = UserEvaluationSerializer(data={
                'interviewer': get_user(id=interviewer_id),
                'interviewee': get_user(id=interviewee_id),
            }, partial=True)
            save_or_raise(serializer)
        return_data['interviews'] = serializer.data  # 添加面试
        return Response(return_data, status=status.HTTP_201_CREATED)

    # @privilege_required('can_participate_interview')
    def put(self, request):
        ''' 交互3 评价面试(有参与面试评价权)'''
        postdata = request.data
        interview_id = postdata.get('interview_id')
        interview = UserEvaluation.objects.filter(id=interview_id).first()
        serializer = UserEvaluationSerializer(instance=interview, data={
            'score': postdata.get('score'),
            'review': postdata.get('review')
        }, partial=True)
        save_or_raise(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # @privilege_required('can_manage_interview')
    def delete(self, request):
        '''交互4 删除UserEvaluation'''
        postdata = request.data
        interview_ids = postdata.get('interview_id', list)
        for interview_id in interview_ids:
            UserEvaluation.objects.filter(id=interview_id).first().delete()
        return Response(status=status.HTTP_200_OK)


class UserEnrollmentAPI(APIView):
    def get(self, request):
        user_enroll = UserEnrollment.objects.all()
        return Response(UserEnrollmentSerializer(user_enroll, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        postdata = request.data
        user_id = get_or_raise(postdata, 'user', int)
        enrollment_id = get_or_raise(postdata, 'enrollment_id', int)
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


class AlumniAPI(APIView):
    def get(self, request):
        user = get_user(user=request.user)
        self_user_enrolls = UserEnrollment.objects.filter(user=user)
        alumni = []
        for user_enroll in self_user_enrolls:
            enrollment = user_enroll.enrollment
            all_user_enroll = UserEnrollment.objects.filter(
                enrollment=enrollment)
            for user_enroll in all_user_enroll:
                alumni.append(user_enroll.user)
        return Response(UserMetaSerializer(alumni, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        postdata = request.data
        user_id = postdata.get('user_id')
        target = get_user(id=user_id)
        user = get_user(user=request.user)
        self_user_enrolls = UserEnrollment.objects.filter(user=user)
        alumni = []
        for user_enroll in self_user_enrolls:
            enrollment = user_enroll.enrollment
            all_user_enroll = UserEnrollment.objects.filter(
                enrollment=enrollment)
            for user_enroll in all_user_enroll:
                alumni.append(user_enroll.user)
        if target in alumni:
            return Response(UserMetaSerializer(target).data, status=status.HTTP_200_OK)
        else:
            return Response({'msg': '对方不是您的校友'}, status=status.HTTP_400_BAD_REQUEST)


class UserCourseAPI(APIView):
    def get(self, request):
        user = get_user(user=request.user)
        user_enrolls = UserEnrollment.objects.filter(
            user=user)
        courses = []
        for user_enroll in user_enrolls:
            enrollment = user_enroll.enrollment
            courses += Course.objects.filter(enrollment=enrollment)
        return Response(CourseSerializer(courses).data, status=status.HTTP_200_OK)

    def post(self, request):
        postdata = request.data
        course_id = postdata.get('course_id')
        course = Course.objects.filter(id=course_id).first()
        return Response(CourseSerializer(course).data, status=status.HTTP_200_OK)


class MangageCourseAPI(APIView):
    # @privilege_required('can_manage_course')
    def get(self, request):

        postdata = request.query_params
        course_id = postdata.get('course_id')
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
        course_id = postdata.get('course_id')
        enrollment_id = postdata.get('enrollment_id')
        name = postdata.get('name')
        description = postdata.get('description')

        course_id = postdata.get('course_id')
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
        course_ids = get_or_raise(postdata, 'course_id', list)
        for course_id in course_ids:
            Course.objects.filter(id=course_id).delete()
        return Response(status=status.HTTP_200_OK)


class SectionAPI(APIView):
    def get(self, request):
        postdata = request.query_params
        course_id = get_or_raise(postdata, 'course_id')
        course = Course.objects.filter(id=course_id).first()
        section = Section.objects.filter(course=course)
        return Response(SectionSerializer(section).data, status=status.HTTP_200_OK)

    def post(self, request):
        postdata = request.data
        course_id = postdata.get('course_id')
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
        section_id = get_or_raise('section_id')
        section = Section.objects.filter(id=section_id).first()
        lessons = Lesson.objects.filter(section=section)
        return Response(LessonSerializer(lessons).data, status=status.HTTP_200_OK)

    def post(self, request):
        postdata = request.data
        return Response(status=status.HTTP_200_OK)
