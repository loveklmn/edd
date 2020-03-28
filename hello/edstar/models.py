from django.db import models
from django.contrib.auth.models import User

from django.contrib.postgres.fields import ArrayField, JSONField


import datetime

from django.utils import timezone


class BaseModel(models.Model):
    '''含时间戳的抽象类'''
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def hard_delete(self):
        self.delete()


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    class Meta:
        abstract = True

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    objects = SoftDeleteManager()

    def delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class UserMeta(SoftDeleteModel):
    '''用户类, 其中 privilege 为8位权限码 sub_field 报名信息'''
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    openId = models.TextField(blank=True, null=False)
    province = models.TextField(blank=True, null=True)
    privilege = models.IntegerField(blank=True, null=True, default=0)
    subField = models.TextField(blank=True, null=True)


class Enrollment(SoftDeleteModel):
    '''课程类, 一组course, 例:一届招生课程的描述 THU 2020 '''
    name = models.TextField(blank=True, null=True)
    pictureUrl = models.TextField(blank=True, null=False)
    description = models.TextField(blank=True, null=True)
    open_status = models.BooleanField(default=True)
    end_at = models.DateTimeField(blank=True, null=True)


class Course(SoftDeleteModel):
    '''一组Section, 例: 算法导论上 算法导论下'''
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    name = models.TextField(blank=True, null=True)  # title
    description = models.TextField(blank=True, null=True)


class Section(SoftDeleteModel):
    '''一组Lesson, 例: 图算法'''
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    name = models.TextField(blank=True, null=True)  # title


class Lesson(SoftDeleteModel):
    '''单次课, 未添加字段, 名片, 文稿, 视频回顾, 文字速记'''
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    order = models.IntegerField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    teacher = models.TextField(blank=True, null=True)
    card = models.TextField(blank=True, null=True)
    slides = models.TextField(default="")
    videos = models.TextField(default="")
    notes = models.TextField(blank=True, null=True)


class UserEnrollment(SoftDeleteModel):
    '''关系类'''
    user = models.ForeignKey(
        UserMeta, on_delete=models.CASCADE,
        related_name="student")
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE,
        related_name="enrollment")  # 届别
    TYPE_OF_STATUS = (
        ('REG', 'register'),
        ('UIN', 'under_interview'),
        ('ACC', 'accept'),
        ('OBS', 'observer'),
        ('REF', 'REFUSED')
    )
    # 4种可能：已报名、面试中、已录取、旁听、已拒绝
    status = models.CharField(max_length=3, choices=TYPE_OF_STATUS)


class UserEvaluation(SoftDeleteModel):
    '''user对其教师的评价'''
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    interviewer = models.ForeignKey(
        UserMeta, related_name="interviewer",
        on_delete=models.CASCADE)
    interviewee = models.ForeignKey(
        UserMeta, related_name="interviewee",
        on_delete=models.CASCADE)
    score = models.IntegerField(blank=True, null=True)
    review = models.TextField(blank=True, null=True)


class Activity(SoftDeleteModel):  # 独立的部:
    '''是对应某一个Class的学生的活动'''
    Enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    pictureUrl = models.TextField(blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    limit = models.IntegerField(default=100, null=False)
    end_at = models.DateTimeField(blank=True, null=True)


class UserActivity(SoftDeleteModel):  # 独立的部:
    '''是对应某一个Class的学生的活动'''
    user = models.ForeignKey(UserMeta, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
