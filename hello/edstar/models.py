from django.db import models
from django.contrib.auth.models import User

from django.contrib.postgres.fields import ArrayField, JSONField


import datetime


def get_default_data():
    return {'msg': 'No value.'}


class BaseModel(models.Model):
    '''含时间戳的抽象类'''
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserMeta(BaseModel):
    '''用户类, 其中 privilege 为8位权限码 sub_field 报名信息'''
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    unionID = models.CharField(max_length=29)
    avatar_url = models.TextField(default="")
    nick_name = models.TextField(default="")
    gender = models.IntegerField(default=0)
    phone = models.TextField(default="")
    birth_date = models.DateField()
    wechat = models.TextField(default="")
    mail = models.EmailField(default="")
    country = models.TextField(default="")
    province = models.TextField(default="")
    city = models.TextField(default="")
    kind = models.TextField(default="")
    privilege = models.IntegerField(default=0)
    sub_field = models.TextField(default="")


class Enrollment(BaseModel):
    '''课程类, 一组course, 例:一届招生课程的描述 THU 2020 '''
    name = models.TextField(default="")
    description = models.TextField(default="")
    open_status = models.BooleanField(default=True)
    end_at = models.DateTimeField()


class Course(BaseModel):
    '''一组Section, 例: 算法导论上 算法导论下'''
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    name = models.TextField(default="")  # title
    description = models.TextField(default="")


class Section(BaseModel):
    '''一组Lesson, 例: 图算法'''
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    name = models.TextField(default="")  # title


class Lesson(BaseModel):
    '''单次课, 未添加字段, 名片, 文稿, 视频回顾, 文字速记'''
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)
    title = models.TextField(default="")
    description = models.TextField(default="")
    teacher = models.TextField(default="")
    card = models.TextField(default="")
    slides = models.FilePathField(default="")
    videos = models.FilePathField(default="")
    notes = models.TextField(default="")


class UserEnrollment(BaseModel):
    '''关系类'''
    user = models.ForeignKey(
        UserMeta, on_delete=models.CASCADE, related_name="student")
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="enrollment")  # 届别

    TYPE_OF_STATUS = (
        ('RE', 'register'),
        ('UI', 'under_interview'),
        ('AC', 'accept'),
        ('OB', 'observer'),
        ('RE', 'REFUSED')
    )
    # 4种可能：已报名、面试中、已录取、旁听、已拒绝
    status = models.CharField(max_length=2, choices=TYPE_OF_STATUS)


class UserEvaluation(BaseModel):
    '''user对其教师的评价'''
    enrollmentId = models.IntegerField(default=0)
    interviewer = models.ForeignKey(
        UserMeta, related_name="interviewer", on_delete=models.CASCADE)
    interviewee = models.ForeignKey(
        UserMeta, related_name="interviewee", on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    review = models.TextField(default="")


class Activity(BaseModel):  # 独立的部:
    '''是对应某一个Class的学生的活动'''
    Enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    name = models.TextField(default="")
    description = models.TextField(default="")


class UserActivity(BaseModel):  # 独立的部:
    '''是对应某一个Class的学生的活动'''
    user = models.ForeignKey(UserMeta, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
