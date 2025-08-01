from django.contrib import admin
from .models import User,Profile,Course,Lesson,LessonProgress,Enrollment,Certificate,Comment,CourseDetails,Activity
from .models import InstructorProfile

# Register your models here.
class CourseAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "instructor":
            kwargs["queryset"] = User.objects.filter(role="instructor")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(User)
admin.site.register(Profile)
admin.site.register(Course, CourseAdmin)
admin.site.register(Lesson)
admin.site.register(Enrollment)
admin.site.register(LessonProgress)
admin.site.register(Comment)
admin.site.register(Certificate)
admin.site.register(CourseDetails)
admin.site.register(Activity)
admin.site.register(InstructorProfile)