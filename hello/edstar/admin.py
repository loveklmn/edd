from django.contrib import admin

from .models import *
# Register your models here.

admin.site.register(UserMeta)
admin.site.register(Enrollment)
admin.site.register(Activity)
admin.site.register(UserEvaluation)
admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(Section)
