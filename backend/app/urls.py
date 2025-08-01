"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from .views import StudentRegisterView, InstructorRegisterView,ProfileViewSet
from .views import CustomTokenObtainPairView ,ChangePasswordView
from rest_framework_simplejwt.views import (
TokenObtainPairView,
TokenRefreshView,
)
from rest_framework.routers import DefaultRouter
from .views import EditMyProfileView, CourseViewSet,CourseDetailViewset,EnrollView,CourseEnrollmentStatusView
from .views import CourseLessonsView
from .views import LessonProgressView
from .views import CourseProgressView
from .views import RecentActivityView
from .views import DayStreakView
from .views import LearningRateView
from .views import LearningHoursView
from .views import PopularCoursesView
from .views import InstructorProfileViewSet, InstructorProfileDetailView, MyInstructorProfileView,MeView
from .views import InstructorDashboardStatsView
from .views import InstructorRecentActivityView
from .views import TopPerformingCoursesView
from .views import LessonViewSet
from .views import InstructorEnrollmentChartView
from .views import InstructorCoursesView
from .views import InstructorCoursesWithDetailsView
from .views import InstructorLessonsView
from .views import CertificateViewSet, UserCertificatesView, CourseCertificatesView, GenerateCertificateView
from .views import CourseEnrollmentsView, CertificateReissueView, TestFileUploadView
from .views import InstructorStudentsView, InstructorStudentDetailView
from .views import AnnouncementViewSet, CourseAnnouncementsView, InstructorAnnouncementsView, StudentAnnouncementsView, AnnouncementDetailView, CreateAnnouncementView
from .views import EnrollmentOverTimeView, LessonsPerCourseView, AnnouncementViewsView, LessonCompletionRateView, StudentEngagementView, CourseCompletionDistributionView, AverageTimePerCourseView, ActivityByDayView
from .views import EnrollmentsAnalyticsView, CompletionAnalyticsView, PerformanceAnalyticsView, EarningsAnalyticsView

router = DefaultRouter()
router.register('profile',ProfileViewSet ,basename='profile')
router.register('courses', CourseViewSet, basename='courses')
router.register('instructor-profiles', InstructorProfileViewSet, basename='instructor-profiles')
router.register('lessons', LessonViewSet, basename='lessons')
router.register('certificates', CertificateViewSet, basename='certificates')
router.register('announcements', AnnouncementViewSet, basename='announcements')
course_details = CourseDetailViewset.as_view({'get': 'retrieve'})

urlpatterns = [
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path('register/student/', StudentRegisterView.as_view(), name='student-register'),
    path('register/instructor/', InstructorRegisterView.as_view(), name='instructor-register'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
          path('api/profile/edit/', EditMyProfileView.as_view(), name='edit-profile'),
        path('change-password/', ChangePasswordView.as_view(), name='change-password'),
        path('course-details/<int:pk>/', course_details, name='course-details'),
        path('enroll/', EnrollView.as_view(), name='enroll'),
        path('enrollment-status/<int:course_id>/', CourseEnrollmentStatusView.as_view(), name='enrollment-status'),
    path('course-lessons/<int:course_id>/', CourseLessonsView.as_view(), name='course-lessons'),
    path('lesson-progress/<int:lesson_id>/', LessonProgressView.as_view(), name='lesson-progress'),
    path('course-progress/<int:course_id>/', CourseProgressView.as_view(), name='course-progress'),
    path('recent-activity/', RecentActivityView.as_view(), name='recent-activity'),
    path('day-streak/', DayStreakView.as_view(), name='day-streak'),
    path('learning-rate/', LearningRateView.as_view(), name='learning-rate'),
    path('learning-hours/', LearningHoursView.as_view(), name='learning-hours'),
    path('popular-courses/', PopularCoursesView.as_view(), name='popular-courses'),
    path('instructor-dashboard-stats/', InstructorDashboardStatsView.as_view(), name='instructor-dashboard-stats'),
     # Instructor Profile routes
     path('instructor-profile/<int:user_id>/', InstructorProfileDetailView.as_view(), name='instructor-profile-detail'),
     path('my-instructor-profile/', MyInstructorProfileView.as_view(), name='my-instructor-profile'),
     path('instructor-recent-activity/', InstructorRecentActivityView.as_view(), name='instructor-recent-activity'),
     path('top-performing-courses/', TopPerformingCoursesView.as_view(), name='top-performing-courses'),
     path('instructor-enrollment-chart/', InstructorEnrollmentChartView.as_view(), name='instructor-enrollment-chart'),
     path('my-courses/', InstructorCoursesView.as_view(), name='my-courses'),
     path("api/me/",MeView.as_view(),name="me")
]

urlpatterns += router.urls
urlpatterns += [
    path('instructor/courses-details/', InstructorCoursesWithDetailsView.as_view(), name='instructor-courses-details'),
    path('instructor/courses/<int:course_id>/lessons/', InstructorLessonsView.as_view(), name='instructor-lessons'),
    path('user/certificates/', UserCertificatesView.as_view(), name='user-certificates'),
    path('courses/<int:course_id>/certificates/', CourseCertificatesView.as_view(), name='course-certificates'),
    path('courses/<int:course_id>/generate-certificate/', GenerateCertificateView.as_view(), name='generate-certificate'),
    path('courses/<int:course_id>/enrollments/', CourseEnrollmentsView.as_view(), name='course-enrollments'),
    path('certificates/<int:certificate_id>/reissue/', CertificateReissueView.as_view(), name='certificate-reissue'),
    path('test-file-upload/', TestFileUploadView.as_view(), name='test-file-upload'),
    path('instructor/students/', InstructorStudentsView.as_view(), name='instructor-students'),
    path('instructor/students/<int:student_id>/', InstructorStudentDetailView.as_view(), name='instructor-student-detail'),
    # Announcement routes
    # Analytics routes
    path('analytics/enrollment-over-time/', EnrollmentOverTimeView.as_view(), name='enrollment-over-time'),
    path('analytics/lessons-per-course/', LessonsPerCourseView.as_view(), name='lessons-per-course'),
    path('analytics/announcement-views/', AnnouncementViewsView.as_view(), name='announcement-views'),
    path('analytics/lesson-completion-rate/', LessonCompletionRateView.as_view(), name='lesson-completion-rate'),
    path('analytics/student-engagement/', StudentEngagementView.as_view(), name='student-engagement'),
    path('analytics/course-completion-distribution/', CourseCompletionDistributionView.as_view(), name='course-completion-distribution'),
    path('analytics/average-time-per-course/', AverageTimePerCourseView.as_view(), name='average-time-per-course'),
    path('analytics/activity-by-day/', ActivityByDayView.as_view(), name='activity-by-day'),
    # New analytics API endpoints for frontend
    path('api/analytics/enrollments/', EnrollmentsAnalyticsView.as_view(), name='enrollments-analytics'),
    path('api/analytics/completion/', CompletionAnalyticsView.as_view(), name='completion-analytics'),
    path('api/analytics/performance/', PerformanceAnalyticsView.as_view(), name='performance-analytics'),
    path('api/analytics/earnings/', EarningsAnalyticsView.as_view(), name='earnings-analytics'),
    path('courses/<int:course_id>/announcements/', CourseAnnouncementsView.as_view(), name='course-announcements'),
    path('instructor/announcements/', InstructorAnnouncementsView.as_view(), name='instructor-announcements'),
    path('student/announcements/', StudentAnnouncementsView.as_view(), name='student-announcements'),
    path('announcements/<int:announcement_id>/', AnnouncementDetailView.as_view(), name='announcement-detail'),
    path('announcements/create/', CreateAnnouncementView.as_view(), name='create-announcement'),
]
