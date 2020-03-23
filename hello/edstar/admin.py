from django.contrib import admin

from .models import UserMeta, Activity, Enrollment, UserEvaluation
# Register your models here.

admin.site.register(UserMeta)
admin.site.register(Enrollment)
admin.site.register(Activity)
admin.site.register(UserEvaluation)
