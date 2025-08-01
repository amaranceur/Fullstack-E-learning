from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import Register
# users/views.py
from rest_framework import viewsets
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer,ProfileSerializer,ChangePasswordSerializer
from .models import Profile,CourseDetails,Activity, Certificate
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Course,Enrollment,Lesson,LessonProgress
from .serializers import CourseSerializer,CourseDetailsSerializer,EnrollSerializer,LessonSerializer
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import NotFound
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncQuarter, ExtractHour
from datetime import date, timedelta
from django.db.models import Count, Sum
from rest_framework import filters
from .models import InstructorProfile
from .serializers import InstructorProfileSerializer, InstructorProfileUpdateSerializer
from django.db import models
from .serializers import CourseWithDetailsSerializer
from .serializers import CertificateSerializer
from django.contrib.auth import get_user_model
from .models import Announcement
from .serializers import AnnouncementSerializer, AnnouncementListSerializer
User = get_user_model()

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    def post(self, request, *args, **kwargs):
        print("Login payload:", request.data)
        return super().post(request, *args, **kwargs)

class StudentRegisterView(APIView):
    def post(self, request):
        print("Student registration payload:", request.data)
        data = request.data.copy()
     
        
        serializer = Register(data=data)
        if serializer.is_valid():
            user = serializer.save()
            Profile.objects.create(user=user)
            return Response({
                'message': 'Student registered successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                   
                }
            }, status=status.HTTP_201_CREATED)
        return Response({
            'message': 'Registration failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class InstructorRegisterView(APIView):
    def post(self, request):
        print("Instructor registration payload:", request.data)
        data = request.data.copy()
        data['is_student'] = False
        data['is_instructor'] = True
        
        serializer = Register(data=data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'Instructor registered successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_student': user.is_student,
                    'is_instructor': user.is_instructor
                }
            }, status=status.HTTP_201_CREATED)
        return Response({
            'message': 'Registration failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST) 
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Profile, Activity
from .serializers import ProfileSerializer

class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer 
    permission_classes = [IsAuthenticated] # ✅ This part is correct
    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

class EditMyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        profile = request.user.profile  # Get the profile of the logged-in user
        serializer = ProfileSerializer(profile, data=request.data, partial=True)  # `partial=True` allows partial updates
        if serializer.is_valid():
            serializer.save()
            # Log activity
            Activity.objects.create(
                user=request.user,
                activity_type='profile_update',
                message='Profile updated.'
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']

            if not user.check_password(old_password):
                return Response({"old_password": "Wrong password."}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()
            return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class IsInstructorOrAdmin(BasePermission):
    """Allow only the instructor of the course or admin to update/delete."""
    def has_object_permission(self, request, view, obj):
        # SAFE_METHODS are always allowed
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        # Only instructor of the course or admin can update/delete
        return (request.user.is_staff or (hasattr(request.user, 'role') and request.user.role == 'instructor' and obj.instructor == request.user))

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all().order_by('-created_at')
    serializer_class = CourseSerializer
    permission_classes=[AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description']
    
    def get_queryset(self):
        queryset = Course.objects.all().order_by('-created_at')
        instructor_id = self.request.query_params.get('instructor', None)
        if instructor_id is not None:
            queryset = queryset.filter(instructor_id=instructor_id)
        return queryset
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsInstructorOrAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        # Set the instructor to the current user
        course = serializer.save(instructor=self.request.user)
        # Auto-enroll the instructor as a student in their own course
        from .models import Enrollment
        Enrollment.objects.create(
            student=self.request.user,
            course=course,
            is_enrolled=True,
            payment_status='accepted',
        )

    def destroy(self, request, *args, **kwargs):
        """Delete a course - only the instructor can delete their own course"""
        course = self.get_object()
        
        # Check if the current user is the instructor of this course
        if course.instructor != request.user:
            return Response(
                {"detail": "You can only delete your own courses."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Delete the course (this will cascade delete related objects)
        course.delete()
        
        return Response(
            {"detail": "Course deleted successfully."}, 
            status=status.HTTP_204_NO_CONTENT
        )
class CourseDetailViewset(viewsets.ModelViewSet):
    queryset = CourseDetails.objects.all()
    serializer_class = CourseDetailsSerializer
    permission_classes = [AllowAny]
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsInstructorOrAdmin()]
        return [IsAuthenticated()]
    def retrieve(self, request, pk=None):
        try:
            # Try to get the Course object
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            raise NotFound("Course not found")

        try:
            # Try to get the CourseDetails using the course
            details = CourseDetails.objects.get(course=course)
        except CourseDetails.DoesNotExist:
            raise NotFound("Course details not found for this course")

        serializer = CourseDetailsSerializer(details)
        return Response(serializer.data)
class EnrollView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        data['student'] = request.user.id  # Set student to logged-in user
        serializer = EnrollSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            Activity.objects.create(
                user=request.user,
                activity_type='enrollment',
                message=f'Enrolled in {serializer.validated_data["course"]}'
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class CourseEnrollmentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)
        user = request.user

        try:
            enrollment = Enrollment.objects.get(student=user, course=course)
            status = enrollment.payment_status 
            return Response({
                "is_enrolled": enrollment.is_enrolled,
                "payment_status": status,
                "enrollment_id": enrollment.id
            })
        except Enrollment.DoesNotExist:
            return Response({
                "is_enrolled": False,
                "payment_status": "not_paid"
            })

class CourseLessonsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        """Fetch all lessons for a course with user's progress"""
        try:
            course = Course.objects.get(id=course_id)
            
            # Check if user is enrolled
            try:
                enrollment = Enrollment.objects.get(student=request.user, course=course)
                if not enrollment.is_enrolled or enrollment.payment_status != 'accepted':
                    return Response({"error": "You must be enrolled to access lessons"}, status=status.HTTP_403_FORBIDDEN)
            except Enrollment.DoesNotExist:
                return Response({"error": "You must be enrolled to access lessons"}, status=status.HTTP_403_FORBIDDEN)
            
            # Get lessons ordered by their order field
            lessons = Lesson.objects.filter(course=course).order_by('order')
            
            # Get user's progress for each lesson
            lessons_data = []
            for lesson in lessons:
                try:
                    progress = LessonProgress.objects.get(student=request.user, lesson=lesson)
                    completed = progress.completed
                except LessonProgress.DoesNotExist:
                    completed = False
                
                lessons_data.append({
                    "id": lesson.id,
                    "title": lesson.title,
                    "content": lesson.content,
                    "video_url": lesson.video_url,
                    "order": lesson.order,
                    "completed": completed
                })
            
            return Response({
                "course_title": course.title,
                "lessons": lessons_data
            })
            
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

class LessonProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, lesson_id):
        """Mark a lesson as completed"""
        try:
            lesson = Lesson.objects.get(id=lesson_id)
            
            # Check if user is enrolled in the course
            try:
                enrollment = Enrollment.objects.get(student=request.user, course=lesson.course)
                if not enrollment.is_enrolled or enrollment.payment_status != 'accepted':
                    return Response({"error": "You must be enrolled to access lessons"}, status=status.HTTP_403_FORBIDDEN)
            except Enrollment.DoesNotExist:
                return Response({"error": "You must be enrolled to access lessons"}, status=status.HTTP_403_FORBIDDEN)
            
            # Create or update lesson progress
            progress, created = LessonProgress.objects.get_or_create(
                student=request.user,
                lesson=lesson,
                defaults={"completed": True, "completed_at": timezone.now()}
            )
            
            if not created:
                progress.completed = True
                progress.completed_at = timezone.now()
                progress.save()
            
            # Log activity
            Activity.objects.create(
                user=request.user,
                activity_type='lesson_completed',
                message=f'Completed lesson: {lesson.title} in course: {lesson.course.title}'
            )

            return Response({
                "message": "Lesson marked as completed",
                "lesson_id": lesson.id,
                "completed": True
            })
            
        except Lesson.DoesNotExist:
            return Response({"error": "Lesson not found"}, status=status.HTTP_404_NOT_FOUND)

class CourseProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        """Get overall progress for a course"""
        try:
            course = Course.objects.get(id=course_id)
            
            # Check if user is enrolled
            try:
                enrollment = Enrollment.objects.get(student=request.user, course=course)
                if not enrollment.is_enrolled or enrollment.payment_status != 'accepted':
                    return Response({"error": "You must be enrolled to access course progress"}, status=status.HTTP_403_FORBIDDEN)
            except Enrollment.DoesNotExist:
                return Response({"error": "You must be enrolled to access course progress"}, status=status.HTTP_403_FORBIDDEN)
            
            # Get total lessons and completed lessons
            total_lessons = Lesson.objects.filter(course=course).count()
            completed_lessons = LessonProgress.objects.filter(
                student=request.user,
                lesson__course=course,
                completed=True
            ).count()
            
            progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
            
            return Response({
                "course_id": course.id,
                "course_title": course.title,
                "total_lessons": total_lessons,
                "completed_lessons": completed_lessons,
                "progress_percentage": round(progress_percentage, 1)
            })
            
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile_picture_url = None
        # If instructor, get from InstructorProfile if exists
        if hasattr(user, 'instructor_profile') and user.role == 'instructor':
            instructor_profile = user.instructor_profile
            if instructor_profile.profile_picture:
                if hasattr(request, 'build_absolute_uri'):
                    profile_picture_url = request.build_absolute_uri(instructor_profile.profile_picture.url)
                else:
                    profile_picture_url = instructor_profile.profile_picture.url
        # If student or fallback, get from Profile
        elif hasattr(user, 'profile'):
            profile = user.profile
            if profile.profile_picture:
                if hasattr(request, 'build_absolute_uri'):
                    profile_picture_url = request.build_absolute_uri(profile.profile_picture.url)
                else:
                    profile_picture_url = profile.profile_picture.url
        return Response({
            "username": user.username,
            "email": user.email,
            "profile_picture": profile_picture_url,
            "role": user.role
        })

class RecentActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        activities = Activity.objects.filter(user=request.user).order_by('-timestamp')[:4]
        data = [
            {
                'activity_type': activity.activity_type,
                'message': activity.message,
                'timestamp': activity.timestamp
            }
            for activity in activities
        ]
        return Response({'activities': data})

class DayStreakView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        activity_dates = (
            Activity.objects.filter(user=request.user)
            .annotate(activity_date=TruncDate('timestamp'))
            .values_list('activity_date', flat=True)
            .distinct()
            .order_by('-activity_date')
        )
        streak = 0
        today = date.today()
        for i, activity_date in enumerate(activity_dates):
            expected_date = today - timedelta(days=i)
            if activity_date == expected_date:
                streak += 1
            else:
                break
        return Response({'streak_days': streak})

class LearningRateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get all courses the user is enrolled in and accepted
        enrolled_courses = Enrollment.objects.filter(student=request.user, is_enrolled=True, payment_status='accepted').values_list('course', flat=True)
        total_lessons = Lesson.objects.filter(course__in=enrolled_courses).count()
        completed_lessons = LessonProgress.objects.filter(student=request.user, lesson__course__in=enrolled_courses, completed=True).count()
        if total_lessons == 0:
            rate = 0.0
        else:
            rate = (completed_lessons / total_lessons) * 100
        return Response({'learning_rate': round(rate, 1)})

class LearningHoursView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        completed_lessons = LessonProgress.objects.filter(student=request.user, completed=True).count()
        avg_minutes_per_lesson = 30
        hours = (completed_lessons * avg_minutes_per_lesson) / 60
        return Response({'learning_hours': round(hours, 1)})

class PopularCoursesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # Annotate courses with enrollment count and order by it
        popular_courses = Course.objects.annotate(
            enrollment_count=Count('enrollments')
        ).order_by('-enrollment_count')[:6]  # Get top 6 popular courses
        
        serializer = CourseSerializer(popular_courses, many=True, context={'request': request})
        return Response(serializer.data)

class IsInstructorProfileOwner(BasePermission):
    """Allow only the owner of the instructor profile or admin to access."""
    def has_object_permission(self, request, view, obj):
        # SAFE_METHODS are always allowed for viewing
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        # Only the profile owner or admin can update/delete
        return (request.user.is_staff or obj.user == request.user)

class InstructorProfileViewSet(viewsets.ModelViewSet):
    serializer_class = InstructorProfileSerializer
    permission_classes = [IsAuthenticated, IsInstructorProfileOwner]
    
    def get_queryset(self):
        # If user is staff, they can see all profiles
        if self.request.user.is_staff:
            return InstructorProfile.objects.all()
        # Otherwise, users can only see their own profile
        return InstructorProfile.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return InstructorProfileUpdateSerializer
        return InstructorProfileSerializer
    
    def perform_create(self, serializer):
        # Set the user to the current user
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        # Update the profile
        serializer.save()
        # Log activity
        Activity.objects.create(
            user=self.request.user,
            activity_type='instructor_profile_update',
            message='Instructor profile updated.'
        )

class InstructorProfileDetailView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        """Get instructor profile by user ID (public access)"""
        try:
            instructor_profile = InstructorProfile.objects.get(user_id=user_id)
            serializer = InstructorProfileSerializer(instructor_profile, context={'request': request})
            return Response(serializer.data)
        except InstructorProfile.DoesNotExist:
            return Response(
                {"detail": "Instructor profile not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )

class MyInstructorProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user's instructor profile"""
        try:
            instructor_profile = InstructorProfile.objects.get(user=request.user)
            serializer = InstructorProfileSerializer(instructor_profile, context={'request': request})
            return Response(serializer.data)
        except InstructorProfile.DoesNotExist:
            return Response(
                {"detail": "Instructor profile not found. Create one first."}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    def post(self, request):
        """Create instructor profile for current user"""
        # Check if profile already exists
        if InstructorProfile.objects.filter(user=request.user).exists():
            return Response(
                {"detail": "Instructor profile already exists."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = InstructorProfileSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            instructor_profile = serializer.save(user=request.user)
            # Log activity
            Activity.objects.create(
                user=request.user,
                activity_type='instructor_profile_created',
                message='Instructor profile created.'
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request):
        """Update current user's instructor profile"""
        try:
            instructor_profile = InstructorProfile.objects.get(user=request.user)
            serializer = InstructorProfileUpdateSerializer(
                instructor_profile, 
                data=request.data, 
                partial=True,
                context={'request': request}
            )
            if serializer.is_valid():
                serializer.save()
                # Log activity
                Activity.objects.create(
                    user=request.user,
                    activity_type='instructor_profile_update',
                    message='Instructor profile updated.'
                )
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except InstructorProfile.DoesNotExist:
            return Response(
                {"detail": "Instructor profile not found. Create one first."}, 
                status=status.HTTP_404_NOT_FOUND
            )

class InstructorDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, 'instructor_profile'):
            return Response({'detail': 'Not an instructor.'}, status=403)
        # Total courses created
        total_courses = Course.objects.filter(instructor=user).count()
        # Total students enrolled (unique students across all their courses)
        course_ids = Course.objects.filter(instructor=user).values_list('id', flat=True)
        total_students = Enrollment.objects.filter(course_id__in=course_ids, is_enrolled=True).values('student').distinct().count()
        # Total lessons uploaded
        total_lessons = Lesson.objects.filter(course_id__in=course_ids).count()
        # Total earnings (real calculation)
        total_earnings = Enrollment.objects.filter(
            course_id__in=course_ids,
            is_enrolled=True,
            payment_status='accepted'
        ).aggregate(total=Sum('amount_paid'))['total'] or 0
        return Response({
            'total_courses': total_courses,
            'total_students': total_students,
            'total_lessons': total_lessons,
            'total_earnings': total_earnings
        })

class InstructorRecentActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Ensure user is an instructor
        if not hasattr(user, 'instructor_profile'):
            return Response({'detail': 'Not an instructor.'}, status=403)

        # Get all course titles taught by this instructor
        course_titles = list(Course.objects.filter(instructor=user).values_list('title', flat=True))

        # Build a Q object to match any course title in the message
        from django.db.models import Q
        title_queries = Q()
        for title in course_titles:
            title_queries |= Q(message__icontains=title)

        activities = Activity.objects.filter(
            (
                Q(activity_type__in=['enrollment', 'lesson_completed', 'certificate']) & title_queries
            ) |
            (
                Q(activity_type='lesson_uploaded') & Q(user=user)
            )
        ).order_by('-timestamp')[:4]

        data = [
            {
                'activity_type': activity.activity_type,
                'message': activity.message,
                'timestamp': activity.timestamp
            }
            for activity in activities
        ]
        return Response({'activities': data})

class TopPerformingCoursesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Ensure user is an instructor
        if not hasattr(user, 'instructor_profile'):
            return Response({'detail': 'Not an instructor.'}, status=403)

        # Get all courses taught by this instructor
        courses = Course.objects.filter(instructor=user)
        data = []
        for course in courses:
            enrolled_count = Enrollment.objects.filter(course=course, is_enrolled=True).count()
            revenue = Enrollment.objects.filter(
                course=course,
                is_enrolled=True,
                payment_status='accepted'
            ).aggregate(total=models.Sum('amount_paid'))['total'] or 0
            data.append({
                'course_title': course.title,
                'enrolled_count': enrolled_count,
                'revenue': revenue
            })
        # Sort by revenue descending
        data = sorted(data, key=lambda x: x['revenue'], reverse=True)
        return Response({'top_performing_courses': data})

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        lesson = serializer.save()
        # Log activity for lesson upload
        Activity.objects.create(
            user=self.request.user,
            activity_type='lesson_uploaded',
            message=f'Uploaded new lesson: {lesson.title} in course: {lesson.course.title}'
        )

class InstructorEnrollmentChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, 'instructor_profile'):
            return Response({'detail': 'Not an instructor.'}, status=403)

        # Get all courses taught by this instructor
        course_ids = Course.objects.filter(instructor=user).values_list('id', flat=True)

        # Get enrollments for these courses, grouped by day
        enrollments_by_day = (
            Enrollment.objects.filter(course_id__in=course_ids, is_enrolled=True)
            .annotate(day=TruncDate('enrolled_at'))
            .values('day')
            .order_by('day')
            .annotate(count=models.Count('student', distinct=True))
        )

        print('DEBUG enrollments_by_day:', list(enrollments_by_day))

        # Optionally, only return the last 30 days
        from datetime import date, timedelta
        today = date.today()
        thirty_days_ago = today - timedelta(days=29)
        chart_data = [
            {"date": (thirty_days_ago + timedelta(days=i)).isoformat(), "count": 0}
            for i in range(30)
        ]
        day_to_index = {d["date"]: i for i, d in enumerate(chart_data)}
        for entry in enrollments_by_day:
            day_str = entry["day"].isoformat()
            if day_str in day_to_index:
                chart_data[day_to_index[day_str]]["count"] = entry["count"]

        print('DEBUG chart_data:', chart_data)

        return Response({"enrollments_over_time": chart_data})

class InstructorCoursesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, 'instructor_profile'):
            return Response({'detail': 'Not an instructor.'}, status=403)
        courses = Course.objects.filter(instructor=user)
        from .serializers import CourseSerializer
        serializer = CourseSerializer(courses, many=True, context={'request': request})
        return Response({'courses': serializer.data})

class InstructorCoursesWithDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, 'instructor_profile'):
            return Response({'detail': 'Not an instructor.'}, status=403)
        courses = Course.objects.filter(instructor=user)
        serializer = CourseWithDetailsSerializer(courses, many=True, context={'request': request})
        return Response({'courses': serializer.data})

    def post(self, request):
        """Create both course and course details in a single request"""
        user = request.user
        if not hasattr(user, 'instructor_profile'):
            return Response({'detail': 'Not an instructor.'}, status=403)
        
        try:
            # Extract course data
            course_data = {
                'title': request.data.get('title'),
                'description': request.data.get('description'),
                'price': request.data.get('price'),
                'category': request.data.get('category'),
                'level': request.data.get('level')
            }
            
            # Handle duration
            duration_hours = int(request.data.get('duration_hours', 0) or 0)
            duration_minutes = int(request.data.get('duration_minutes', 0) or 0)
            
            if duration_hours > 0 or duration_minutes > 0:
                duration_parts = []
                if duration_hours > 0:
                    duration_parts.append(f"{duration_hours}h")
                if duration_minutes > 0:
                    duration_parts.append(f"{duration_minutes}m")
                course_data['duration'] = ' '.join(duration_parts)
            else:
                course_data['duration'] = ''
            
            # Handle image upload
            if 'image' in request.FILES:
                course_data['image'] = request.FILES['image']
            
            # Create course
            course_serializer = CourseSerializer(data=course_data, context={'request': request})
            if course_serializer.is_valid():
                course = course_serializer.save(instructor=user)
                
                # Auto-enroll instructor in their own course
                from .models import Enrollment
                Enrollment.objects.create(
                    student=user,
                    course=course,
                    is_enrolled=True,
                    payment_status='accepted',
                )
                
                # Extract course details data
                details_data = {
                    'course': course.id,
                    'requirements': request.data.get('requirements', ''),
                    'what_you_will_learn': request.data.get('what_you_will_learn', ''),
                    'curriculum': request.data.get('curriculum', '')
                }
                
                # Create course details directly
                from .models import CourseDetails
                CourseDetails.objects.create(
                    course=course,
                    requirements=details_data['requirements'],
                    what_you_will_learn=details_data['what_you_will_learn'],
                    curriculum=details_data['curriculum']
                )
                
                # Return the complete course with details
                complete_serializer = CourseWithDetailsSerializer(course, context={'request': request})
                return Response(complete_serializer.data, status=201)
            else:
                return Response(course_serializer.errors, status=400)
                
        except Exception as e:
            return Response({'detail': str(e)}, status=500)

class InstructorLessonsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        """Get all lessons for a course (instructor only)"""
        user = request.user
        if not hasattr(user, 'instructor_profile'):
            return Response({'detail': 'Not an instructor.'}, status=403)
        
        try:
            course = Course.objects.get(id=course_id, instructor=user)
            lessons = Lesson.objects.filter(course=course).order_by('order')
            
            lessons_data = []
            for lesson in lessons:
                lessons_data.append({
                    "id": lesson.id,
                    "title": lesson.title,
                    "content": lesson.content,
                    "video_url": lesson.video_url,
                    "order": lesson.order,
                  
                })
            
            return Response({
                "course_title": course.title,
                "lessons": lessons_data
            })
            
        except Course.DoesNotExist:
            return Response({"error": "Course not found or you don't have permission to access it"}, status=status.HTTP_404_NOT_FOUND)

class CertificateViewSet(viewsets.ModelViewSet):
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see their own certificates
        return Certificate.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        certificate = serializer.save(user=self.request.user)
        # Log activity
        Activity.objects.create(
            user=self.request.user,
            activity_type='certificate',
            message=f'Earned certificate for course: {certificate.course.title}'
        )

class UserCertificatesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all certificates for the current user"""
        certificates = Certificate.objects.filter(user=request.user)
        serializer = CertificateSerializer(certificates, many=True, context={'request': request})
        return Response({'certificates': serializer.data})

class CourseCertificatesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Get certificates for a specific course (instructor only)"""
        try:
            course = Course.objects.get(id=course_id)
            
            # Check if user is the instructor
            if course.instructor != request.user:
                return Response({"error": "You don't have permission to view these certificates"}, status=status.HTTP_403_FORBIDDEN)
            
            certificates = Certificate.objects.filter(course=course)
            serializer = CertificateSerializer(certificates, many=True, context={'request': request})
            return Response({'certificates': serializer.data})
            
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

class GenerateCertificateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, course_id):
        """Generate a certificate for a user who completed a course"""
        try:
            course = Course.objects.get(id=course_id)
            
            # Check if user is the instructor
            if course.instructor != request.user:
                return Response({"error": "You don't have permission to issue certificates for this course"}, status=status.HTTP_403_FORBIDDEN)
            
            # Get student ID from request
            student_id = request.data.get('student_id')
            if not student_id:
                return Response({"error": "Student ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                student = User.objects.get(id=student_id)
            except User.DoesNotExist:
                return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if student is enrolled in the course
            try:
                enrollment = Enrollment.objects.get(student=student, course=course)
                if not enrollment.is_enrolled or enrollment.payment_status != 'accepted':
                    return Response({"error": "Student must be enrolled to receive a certificate"}, status=status.HTTP_403_FORBIDDEN)
            except Enrollment.DoesNotExist:
                return Response({"error": "Student must be enrolled to receive a certificate"}, status=status.HTTP_403_FORBIDDEN)
            
            # Check if student has already received a certificate for this course
            if Certificate.objects.filter(user=student, course=course).exists():
                return Response({"error": "Certificate already exists for this student and course"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if student has completed all lessons (you can modify this logic)
            total_lessons = course.lessons.count()
            completed_lessons = LessonProgress.objects.filter(
                student=student,
                lesson__course=course,
                completed=True
            ).count()
            
            if completed_lessons < total_lessons:
                return Response({"error": "Student must complete all lessons to receive a certificate"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Debug: Print request data
            print("Request data:", request.data)
            print("Request FILES:", request.FILES)
            
            # Create certificate
            certificate_data = {
                'user': student,
                'course': course
            }
            
            # Handle file upload if provided
            if 'certificate_file' in request.FILES:
                certificate_file = request.FILES['certificate_file']
                print("Certificate file received:", certificate_file.name, certificate_file.size)
                
                # Validate file type
                allowed_types = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']
                if certificate_file.content_type not in allowed_types:
                    return Response({
                        "error": "Invalid file type. Please upload PDF, JPG, JPEG, or PNG files only."
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Validate file size (10MB limit)
                if certificate_file.size > 10 * 1024 * 1024:  # 10MB
                    return Response({
                        "error": "File size too large. Please upload files smaller than 10MB."
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                certificate_data['certificate_file'] = certificate_file
            else:
                print("No certificate file in request.FILES")
                # You can make file optional or required
                # return Response({"error": "Certificate file is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            certificate = Certificate.objects.create(**certificate_data)
            
            # Log activity
            Activity.objects.create(
                user=request.user,
                activity_type='certificate',
                message=f'Issued certificate for course: {course.title} to student: {student.username}'
            )
            
            serializer = CertificateSerializer(certificate, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print("Error creating certificate:", str(e))
            return Response({"error": f"Failed to create certificate: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CourseEnrollmentsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Get all enrolled students for a course (instructor only)"""
        try:
            course = Course.objects.get(id=course_id)
            
            # Check if user is the instructor
            if course.instructor != request.user:
                return Response({"error": "You don't have permission to view these enrollments"}, status=status.HTTP_403_FORBIDDEN)
            
            enrollments = Enrollment.objects.filter(course=course, is_enrolled=True)
            
            enrollments_data = []
            for enrollment in enrollments:
                # Get student's lesson progress
                total_lessons = course.lessons.count()
                completed_lessons = LessonProgress.objects.filter(
                    student=enrollment.student,
                    lesson__course=course,
                    completed=True
                ).count()
                
                enrollments_data.append({
                    "id": enrollment.student.id,
                    "student_name": f"{enrollment.student.first_name} {enrollment.student.last_name}".strip() or enrollment.student.username,
                    "student_username": enrollment.student.username,
                    "student_email": enrollment.student.email,
                    "enrolled_at": enrollment.enrolled_at,
                    "total_lessons": total_lessons,
                    "completed_lessons": completed_lessons,
                    "completion_percentage": (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
                })
            
            return Response({'enrollments': enrollments_data})
            
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

class CertificateReissueView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, certificate_id):
        """Reissue a certificate (instructor only)"""
        try:
            certificate = Certificate.objects.get(id=certificate_id)
            
            # Check if user is the instructor of the course
            if certificate.course.instructor != request.user:
                return Response({"error": "You don't have permission to reissue this certificate"}, status=status.HTTP_403_FORBIDDEN)
            
            # Generate new certificate ID
            import uuid
            certificate.certificate_id = str(uuid.uuid4())
            certificate.save()
            
            # Log activity
            Activity.objects.create(
                user=request.user,
                activity_type='certificate',
                message=f'Reissued certificate for course: {certificate.course.title} to student: {certificate.user.username}'
            )
            
            serializer = CertificateSerializer(certificate, context={'request': request})
            return Response(serializer.data)
            
        except Certificate.DoesNotExist:
            return Response({"error": "Certificate not found"}, status=status.HTTP_404_NOT_FOUND)

class TestFileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Test endpoint for file uploads"""
        print("Test file upload - Request data:", request.data)
        print("Test file upload - Request FILES:", request.FILES)
        
        if 'file' in request.FILES:
            file = request.FILES['file']
            print("File received:", file.name, file.size, file.content_type)
            return Response({
                "message": "File uploaded successfully",
                "filename": file.name,
                "size": file.size,
                "type": file.content_type
            })
        else:
            return Response({"error": "No file received"}, status=status.HTTP_400_BAD_REQUEST)

class InstructorStudentsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all enrolled students across all courses for an instructor"""
        user = request.user
        
        # Ensure user is an instructor
        if not hasattr(user, 'instructor_profile'):
            return Response({'detail': 'Not an instructor.'}, status=403)
        
        # Get all courses taught by this instructor
        courses = Course.objects.filter(instructor=user)
        
        # Get all enrollments for these courses
        enrollments = Enrollment.objects.filter(
            course__in=courses,
            is_enrolled=True,
            payment_status='accepted'
        ).select_related('student', 'course')
        
        # Group students by unique student (in case they're enrolled in multiple courses)
        students_data = {}
        
        for enrollment in enrollments:
            student = enrollment.student
            course = enrollment.course
            
            if student.id not in students_data:
                # Initialize student data
                students_data[student.id] = {
                    "id": student.id,
                    "name": f"{student.first_name} {student.last_name}".strip() or student.username,
                    "username": student.username,
                    "email": student.email,
                    "phone": getattr(student, 'phone', ''),  # Add phone field if exists
                    "avatar": None,  # Will be set below
                    "enrollment_date": enrollment.enrolled_at,
                    "courses": [],
                    "total_courses": 0,
                    "total_progress": 0,
                    "status": "active",  # Default status
                    "last_activity": None
                }
                
                # Get profile picture
                try:
                    profile = student.profile
                    if profile.profile_picture:
                        students_data[student.id]["avatar"] = request.build_absolute_uri(profile.profile_picture.url)
                except Profile.DoesNotExist:
                    pass
            
            # Add course info
            course_info = {
                "course_id": course.id,
                "course_title": course.title,
                "enrolled_at": enrollment.enrolled_at,
                "total_lessons": course.lessons.count(),
                "completed_lessons": LessonProgress.objects.filter(
                    student=student,
                    lesson__course=course,
                    completed=True
                ).count()
            }
            
            # Calculate progress percentage
            if course_info["total_lessons"] > 0:
                course_info["progress_percentage"] = (course_info["completed_lessons"] / course_info["total_lessons"]) * 100
            else:
                course_info["progress_percentage"] = 0
            
            students_data[student.id]["courses"].append(course_info)
        
        # Calculate overall stats for each student
        for student_id, student_data in students_data.items():
            student_data["total_courses"] = len(student_data["courses"])
            
            # Calculate average progress across all courses
            if student_data["total_courses"] > 0:
                total_progress = sum(course["progress_percentage"] for course in student_data["courses"])
                student_data["total_progress"] = round(total_progress / student_data["total_courses"], 1)
            
            # Determine status based on progress and activity
            if student_data["total_progress"] >= 80:
                student_data["status"] = "completed"
            elif student_data["total_progress"] >= 20:
                student_data["status"] = "active"
            else:
                student_data["status"] = "inactive"
            
            # Get last activity (most recent lesson completion or enrollment)
            last_activity = Activity.objects.filter(
                user_id=student_id,
                activity_type__in=['lesson_completed', 'enrollment']
            ).order_by('-timestamp').first()
            
            if last_activity:
                student_data["last_activity"] = last_activity.timestamp
        
        # Convert to list and sort by enrollment date (newest first)
        students_list = list(students_data.values())
        students_list.sort(key=lambda x: x["enrollment_date"], reverse=True)
        
        # Add summary statistics
        total_students = len(students_list)
        active_students = len([s for s in students_list if s["status"] == "active"])
        completed_students = len([s for s in students_list if s["status"] == "completed"])
        inactive_students = len([s for s in students_list if s["status"] == "inactive"])
        
        avg_progress = 0
        if total_students > 0:
            avg_progress = sum(s["total_progress"] for s in students_list) / total_students
        
        return Response({
            "students": students_list,
            "summary": {
                "total_students": total_students,
                "active_students": active_students,
                "completed_students": completed_students,
                "inactive_students": inactive_students,
                "average_progress": round(avg_progress, 1)
            }
        })

class InstructorStudentDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, student_id):
        """Get detailed student information for an instructor"""
        user = request.user
        
        # Ensure user is an instructor
        if not hasattr(user, 'instructor_profile'):
            return Response({'detail': 'Not an instructor.'}, status=403)
        
        try:
            # Get the student
            student = User.objects.get(id=student_id)
            
            # Get all courses taught by this instructor
            instructor_courses = Course.objects.filter(instructor=user)
            
            # Get enrollments for this student in instructor's courses
            enrollments = Enrollment.objects.filter(
                student=student,
                course__in=instructor_courses,
                is_enrolled=True,
                payment_status='accepted'
            ).select_related('course')
            
            if not enrollments.exists():
                return Response({'detail': 'Student not found in your courses.'}, status=404)
            
            # Get student profile
            try:
                profile = student.profile
                profile_picture = None
                if profile.profile_picture:
                    profile_picture = request.build_absolute_uri(profile.profile_picture.url)
            except Profile.DoesNotExist:
                profile_picture = None
            
            # Get detailed course progress
            courses_data = []
            total_lessons = 0
            total_completed_lessons = 0
            
            for enrollment in enrollments:
                course = enrollment.course
                
                # Get all lessons for this course
                lessons = Lesson.objects.filter(course=course).order_by('order')
                course_total_lessons = lessons.count()
                
                # Get completed lessons for this student
                completed_lessons = LessonProgress.objects.filter(
                    student=student,
                    lesson__course=course,
                    completed=True
                ).count()
                
                # Calculate progress
                progress_percentage = (completed_lessons / course_total_lessons * 100) if course_total_lessons > 0 else 0
                
                # Get lesson details
                lessons_data = []
                for lesson in lessons:
                    try:
                        progress = LessonProgress.objects.get(student=student, lesson=lesson)
                        completed = progress.completed
                        completed_at = progress.completed_at
                    except LessonProgress.DoesNotExist:
                        completed = False
                        completed_at = None
                    
                    lessons_data.append({
                        "id": lesson.id,
                        "title": lesson.title,
                        "order": lesson.order,
                        "completed": completed,
                        "completed_at": completed_at
                    })
                
                courses_data.append({
                    "course_id": course.id,
                    "course_title": course.title,
                    "enrolled_at": enrollment.enrolled_at,
                    "total_lessons": course_total_lessons,
                    "completed_lessons": completed_lessons,
                    "progress_percentage": round(progress_percentage, 1),
                    "lessons": lessons_data
                })
                
                total_lessons += course_total_lessons
                total_completed_lessons += completed_lessons
            
            # Get student activity
            activities = Activity.objects.filter(
                user=student,
                activity_type__in=['lesson_completed', 'enrollment', 'certificate']
            ).order_by('-timestamp')[:10]
            
            activities_data = []
            for activity in activities:
                activities_data.append({
                    "type": activity.activity_type,
                    "message": activity.message,
                    "timestamp": activity.timestamp
                })
            
            # Get certificates
            certificates = Certificate.objects.filter(
                user=student,
                course__in=instructor_courses
            ).select_related('course')
            
            certificates_data = []
            for certificate in certificates:
                certificates_data.append({
                    "id": certificate.id,
                    "course_title": certificate.course.title,
                    "issue_date": certificate.issue_date,
                    "certificate_file_url": request.build_absolute_uri(certificate.certificate_file.url) if certificate.certificate_file else None
                })
            
            # Calculate overall stats
            overall_progress = (total_completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
            
            # Determine status
            if overall_progress >= 80:
                status = "completed"
            elif overall_progress >= 20:
                status = "active"
            else:
                status = "inactive"
            
            return Response({
                "student": {
                    "id": student.id,
                    "username": student.username,
                    "name": f"{student.first_name} {student.last_name}".strip() or student.username,
                    "email": student.email,
                    "phone": getattr(student, 'phone', ''),
                    "profile_picture": profile_picture,
                    "date_joined": student.date_joined,
                    "status": status,
                    "overall_progress": round(overall_progress, 1),
                    "total_courses": len(courses_data),
                    "total_lessons": total_lessons,
                    "total_completed_lessons": total_completed_lessons
                },
                "courses": courses_data,
                "activities": activities_data,
                "certificates": certificates_data
            })
            
        except User.DoesNotExist:
            return Response({'detail': 'Student not found.'}, status=404)

class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # If user is staff, they can see all announcements
        if user.is_staff:
            return Announcement.objects.all().order_by('-created_at')
        
        # If user is an instructor, they can see their own announcements
        if hasattr(user, 'instructor_profile'):
            return Announcement.objects.filter(instructor=user).order_by('-created_at')
        
        # If user is a student, they can see published announcements for courses they're enrolled in
        enrolled_courses = Enrollment.objects.filter(
            student=user, 
            is_enrolled=True, 
            payment_status='accepted'
        ).values_list('course', flat=True)
        
        return Announcement.objects.filter(
            course__in=enrolled_courses,
            is_published=True
        ).order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AnnouncementListSerializer
        return AnnouncementSerializer
    
    def perform_create(self, serializer):
        announcement = serializer.save()
        # Log activity
        Activity.objects.create(
            user=self.request.user,
            activity_type='announcement_created',
            message=f'Created announcement: {announcement.title} for course: {announcement.course.title}'
        )
    
    def perform_update(self, serializer):
        announcement = serializer.save()
        # Log activity
        Activity.objects.create(
            user=self.request.user,
            activity_type='announcement_updated',
            message=f'Updated announcement: {announcement.title} for course: {announcement.course.title}'
        )
    
    def perform_destroy(self, instance):
        # Log activity before deletion
        Activity.objects.create(
            user=self.request.user,
            activity_type='announcement_deleted',
            message=f'Deleted announcement: {instance.title} for course: {instance.course.title}'
        )
        instance.delete()

class CourseAnnouncementsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Get all announcements for a specific course"""
        try:
            course = Course.objects.get(id=course_id)
            
            # Check if user has access to this course
            user = request.user
            
            # If user is the instructor of the course
            if course.instructor == user:
                announcements = Announcement.objects.filter(course=course).order_by('-created_at')
            # If user is enrolled in the course
            elif Enrollment.objects.filter(student=user, course=course, is_enrolled=True, payment_status='accepted').exists():
                announcements = Announcement.objects.filter(course=course, is_published=True).order_by('-created_at')
            else:
                return Response({"error": "You don't have permission to view announcements for this course"}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = AnnouncementListSerializer(announcements, many=True, context={'request': request})
            return Response({'announcements': serializer.data})
            
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

class InstructorAnnouncementsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all announcements created by the current instructor"""
        user = request.user
        
        # Ensure user is an instructor
        if not hasattr(user, 'instructor_profile'):
            return Response({'detail': 'Not an instructor.'}, status=403)
        
        announcements = Announcement.objects.filter(instructor=user).order_by('-created_at')
        serializer = AnnouncementListSerializer(announcements, many=True, context={'request': request})
        return Response({'announcements': serializer.data})

class StudentAnnouncementsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all announcements for courses the student is enrolled in"""
        user = request.user
        
        # Get all courses the student is enrolled in
        enrolled_courses = Enrollment.objects.filter(
            student=user, 
            is_enrolled=True, 
            payment_status='accepted'
        ).values_list('course', flat=True)
        
        announcements = Announcement.objects.filter(
            course__in=enrolled_courses,
            is_published=True
        ).order_by('-created_at')
        
        serializer = AnnouncementListSerializer(announcements, many=True, context={'request': request})
        return Response({'announcements': serializer.data})

class AnnouncementDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, announcement_id):
        """Get a specific announcement"""
        try:
            announcement = Announcement.objects.get(id=announcement_id)
            
            # Check if user has access to this announcement
            user = request.user
            
            # If user is the instructor who created the announcement
            if announcement.instructor == user:
                pass  # Allow access
            # If user is enrolled in the course and announcement is published
            elif (Enrollment.objects.filter(student=user, course=announcement.course, is_enrolled=True, payment_status='accepted').exists() 
                  and announcement.is_published):
                pass  # Allow access
            else:
                return Response({"error": "You don't have permission to view this announcement"}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = AnnouncementSerializer(announcement, context={'request': request})
            return Response(serializer.data)
            
        except Announcement.DoesNotExist:
            return Response({"error": "Announcement not found"}, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, announcement_id):
        """Update an announcement"""
        try:
            announcement = Announcement.objects.get(id=announcement_id)
            
            # Only the instructor who created the announcement can update it
            if announcement.instructor != request.user:
                return Response({"error": "You don't have permission to update this announcement"}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = AnnouncementSerializer(announcement, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Announcement.DoesNotExist:
            return Response({"error": "Announcement not found"}, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, announcement_id):
        """Delete an announcement"""
        try:
            announcement = Announcement.objects.get(id=announcement_id)
            
            # Only the instructor who created the announcement can delete it
            if announcement.instructor != request.user:
                return Response({"error": "You don't have permission to delete this announcement"}, status=status.HTTP_403_FORBIDDEN)
            
            announcement.delete()
            return Response({"message": "Announcement deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
            
        except Announcement.DoesNotExist:
            return Response({"error": "Announcement not found"}, status=status.HTTP_404_NOT_FOUND)

# Analytics Views
class EnrollmentOverTimeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.GET.get('days', 30))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get enrollments grouped by date
        enrollments = Enrollment.objects.filter(
            enrolled_at__range=(start_date, end_date)
        ).annotate(
            date=TruncDate('enrolled_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # Fill in missing dates with 0
        date_range = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            date_range.append(current_date)
            current_date += timedelta(days=1)
        
        enrollment_dict = {item['date']: item['count'] for item in enrollments}
        data = [
            {
                'date': date.strftime('%Y-%m-%d'),
                'count': enrollment_dict.get(date, 0)
            }
            for date in date_range
        ]
        
        return Response({'data': data})

class LessonsPerCourseView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get courses with lesson counts for the current instructor
        courses = Course.objects.filter(
            instructor=request.user
        ).annotate(
            lesson_count=Count('lessons')
        ).values('id', 'title', 'lesson_count')
        
        data = [
            {
                'course_id': course['id'],
                'course_title': course['title'],
                'lesson_count': course['lesson_count']
            }
            for course in courses
        ]
        
        return Response({'data': data})

class AnnouncementViewsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get announcements with view counts (placeholder - you might need to add a views field)
        announcements = Announcement.objects.filter(
            instructor=request.user
        ).values('id', 'title', 'created_at')
        
        data = [
            {
                'id': announcement['id'],
                'title': announcement['title'],
                'views': 0  # Placeholder - implement actual view tracking
            }
            for announcement in announcements
        ]
        
        return Response({'data': data})

class LessonCompletionRateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get completion statistics for instructor's courses
        total_lessons = Lesson.objects.filter(course__instructor=request.user).count()
        completed_lessons = LessonProgress.objects.filter(
            lesson__course__instructor=request.user,
            completed=True
        ).count()
        in_progress_lessons = LessonProgress.objects.filter(
            lesson__course__instructor=request.user,
            completed=False
        ).count()
        not_started = total_lessons - completed_lessons - in_progress_lessons
        
        data = {
            'completed': completed_lessons,
            'in_progress': in_progress_lessons,
            'not_started': max(0, not_started)
        }
        
        return Response({'data': data})

class StudentEngagementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get student engagement scores based on activity
        enrollments = Enrollment.objects.filter(
            course__instructor=request.user,
            is_enrolled=True
        ).select_related('student', 'course')
        
        data = []
        for enrollment in enrollments:
            # Calculate engagement score based on various factors
            lesson_progress = LessonProgress.objects.filter(
                lesson__course=enrollment.course,
                student=enrollment.student
            )
            
            completed_lessons = lesson_progress.filter(completed=True).count()
            total_lessons = enrollment.course.lessons.count()
            progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
            
            # Activity score based on recent activity
            recent_activity = Activity.objects.filter(
                user=enrollment.student,
                activity_type__in=['lesson_completed', 'enrollment'],
                timestamp__gte=timezone.now() - timedelta(days=30)
            ).count()
            
            engagement_score = min(100, (progress_percentage * 0.7) + (recent_activity * 10))
            
            data.append({
                'student_id': enrollment.student.id,
                'student_name': enrollment.student.username,
                'course_title': enrollment.course.title,
                'activity_score': round(engagement_score, 1),
                'progress_percentage': round(progress_percentage, 1)
            })
        
        # Sort by engagement score
        data.sort(key=lambda x: x['activity_score'], reverse=True)
        
        return Response({'data': data})

class CourseCompletionDistributionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get completion rates for each course
        courses = Course.objects.filter(instructor=request.user)
        
        data = []
        for course in courses:
            total_enrollments = course.enrollments.filter(is_enrolled=True).count()
            completed_enrollments = course.enrollments.filter(
                is_enrolled=True,
                student__lessonprogress__lesson__course=course,
                student__lessonprogress__completed=True
            ).distinct().count()
            
            completion_rate = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
            
            data.append({
                'course_id': course.id,
                'course_title': course.title,
                'completion_rate': round(completion_rate, 1),
                'total_enrollments': total_enrollments,
                'completed_enrollments': completed_enrollments
            })
        
        return Response({'data': data})

class AverageTimePerCourseView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Calculate average time spent per course (placeholder implementation)
        courses = Course.objects.filter(instructor=request.user)
        
        data = []
        for course in courses:
            # This is a simplified calculation - you might want to track actual time spent
            enrollments = course.enrollments.filter(is_enrolled=True).count()
            lessons = course.lessons.count()
            
            # Estimate: 30 minutes per lesson on average
            estimated_hours = (lessons * 30) / 60
            
            data.append({
                'course_id': course.id,
                'course_title': course.title,
                'average_hours': round(estimated_hours, 1),
                'total_lessons': lessons,
                'total_enrollments': enrollments
            })
        
        return Response({'data': data})

class ActivityByDayView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.GET.get('days', 30))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get activity counts by day
        activities = Activity.objects.filter(
            timestamp__range=(start_date, end_date)
        ).annotate(
            date=TruncDate('timestamp')
        ).values('date').annotate(
            activity_count=Count('id')
        ).order_by('date')
        
        # Fill in missing dates with 0
        date_range = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            date_range.append(current_date)
            current_date += timedelta(days=1)
        
        activity_dict = {item['date']: item['activity_count'] for item in activities}
        data = [
            {
                'date': date.strftime('%Y-%m-%d'),
                'activity_count': activity_dict.get(date, 0)
            }
            for date in date_range
        ]
        
        return Response({'data': data})

class CreateAnnouncementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AnnouncementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(instructor=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# New Analytics Views for Frontend
class EnrollmentsAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get query parameters
        date_range = int(request.GET.get('date_range', 30))
        course = request.GET.get('course', 'all')
        timeframe = request.GET.get('timeframe', 'daily')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        # Calculate date range
        end_date_obj = timezone.now()
        if end_date:
            end_date_obj = timezone.datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        
        start_date_obj = end_date_obj - timedelta(days=date_range)
        if start_date:
            start_date_obj = timezone.datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)

        # Check if user has any courses
        user_courses = Course.objects.filter(instructor=request.user)
        if not user_courses.exists():
            # Return mock data if no courses exist
            return Response({
                'dailyEnrollments': [
                    {'date': '2024-01-01', 'count': 12, 'revenue': 1200},
                    {'date': '2024-01-02', 'count': 18, 'revenue': 1800},
                    {'date': '2024-01-03', 'count': 15, 'revenue': 1500},
                    {'date': '2024-01-04', 'count': 22, 'revenue': 2200},
                    {'date': '2024-01-05', 'count': 28, 'revenue': 2800},
                    {'date': '2024-01-06', 'count': 35, 'revenue': 3500},
                    {'date': '2024-01-07', 'count': 42, 'revenue': 4200}
                ],
                'weeklyEnrollments': [
                    {'week': 'Week 1', 'count': 85, 'revenue': 8500},
                    {'week': 'Week 2', 'count': 92, 'revenue': 9200},
                    {'week': 'Week 3', 'count': 78, 'revenue': 7800},
                    {'week': 'Week 4', 'count': 105, 'revenue': 10500}
                ],
                'monthlyEnrollments': [
                    {'month': 'January', 'count': 320, 'revenue': 32000},
                    {'month': 'February', 'count': 285, 'revenue': 28500},
                    {'month': 'March', 'count': 310, 'revenue': 31000},
                    {'month': 'April', 'count': 295, 'revenue': 29500}
                ],
                'courseEnrollments': [
                    {'course': 'React Development', 'enrollments': 45, 'revenue': 4500},
                    {'course': 'Python Programming', 'enrollments': 38, 'revenue': 3800},
                    {'course': 'Web Design', 'enrollments': 32, 'revenue': 3200},
                    {'course': 'Data Science', 'enrollments': 28, 'revenue': 2800}
                ],
                'enrollmentTrends': [
                    {'period': 'Q1', 'growth': 15, 'trend': 'up'},
                    {'period': 'Q2', 'growth': 8, 'trend': 'up'},
                    {'period': 'Q3', 'growth': -3, 'trend': 'down'},
                    {'period': 'Q4', 'growth': 12, 'trend': 'up'}
                ],
                'peakEnrollmentTimes': [
                    {'hour': '9 AM', 'count': 25},
                    {'hour': '10 AM', 'count': 35},
                    {'hour': '11 AM', 'count': 42},
                    {'hour': '2 PM', 'count': 38},
                    {'hour': '3 PM', 'count': 45},
                    {'hour': '4 PM', 'count': 32}
                ],
                'conversionRates': [
                    {'source': 'Organic Search', 'rate': 12.5, 'visitors': 1200},
                    {'source': 'Social Media', 'rate': 8.3, 'visitors': 800},
                    {'source': 'Email Marketing', 'rate': 15.2, 'visitors': 500},
                    {'source': 'Direct Traffic', 'rate': 6.8, 'visitors': 300}
                ]
            })

        # Filter enrollments
        enrollments_query = Enrollment.objects.filter(
            enrolled_at__range=(start_date_obj, end_date_obj),
            course__instructor=request.user
        )
        
        if course != 'all':
            enrollments_query = enrollments_query.filter(course__title__icontains=course)

        # Check if there are any enrollments
        if not enrollments_query.exists():
            # Return mock data if no enrollments exist
            return Response({
                'dailyEnrollments': [
                    {'date': '2024-01-01', 'count': 0, 'revenue': 0},
                    {'date': '2024-01-02', 'count': 0, 'revenue': 0},
                    {'date': '2024-01-03', 'count': 0, 'revenue': 0},
                    {'date': '2024-01-04', 'count': 0, 'revenue': 0},
                    {'date': '2024-01-05', 'count': 0, 'revenue': 0},
                    {'date': '2024-01-06', 'count': 0, 'revenue': 0},
                    {'date': '2024-01-07', 'count': 0, 'revenue': 0}
                ],
                'weeklyEnrollments': [
                    {'week': 'Week 1', 'count': 0, 'revenue': 0},
                    {'week': 'Week 2', 'count': 0, 'revenue': 0},
                    {'week': 'Week 3', 'count': 0, 'revenue': 0},
                    {'week': 'Week 4', 'count': 0, 'revenue': 0}
                ],
                'monthlyEnrollments': [
                    {'month': 'January', 'count': 0, 'revenue': 0},
                    {'month': 'February', 'count': 0, 'revenue': 0},
                    {'month': 'March', 'count': 0, 'revenue': 0},
                    {'month': 'April', 'count': 0, 'revenue': 0}
                ],
                'courseEnrollments': [
                    {'course': course.title, 'enrollments': 0, 'revenue': 0}
                    for course in user_courses[:5]
                ],
                'enrollmentTrends': [
                    {'period': 'Q1', 'growth': 0, 'trend': 'up'},
                    {'period': 'Q2', 'growth': 0, 'trend': 'up'},
                    {'period': 'Q3', 'growth': 0, 'trend': 'up'},
                    {'period': 'Q4', 'growth': 0, 'trend': 'up'}
                ],
                'peakEnrollmentTimes': [
                    {'hour': '9 AM', 'count': 0},
                    {'hour': '10 AM', 'count': 0},
                    {'hour': '11 AM', 'count': 0},
                    {'hour': '2 PM', 'count': 0},
                    {'hour': '3 PM', 'count': 0},
                    {'hour': '4 PM', 'count': 0}
                ],
                'conversionRates': [
                    {'source': 'Organic Search', 'rate': 0, 'visitors': 0},
                    {'source': 'Social Media', 'rate': 0, 'visitors': 0},
                    {'source': 'Email Marketing', 'rate': 0, 'visitors': 0},
                    {'source': 'Direct Traffic', 'rate': 0, 'visitors': 0}
                ]
            })

        # Generate data based on timeframe
        if timeframe == 'daily':
            daily_data = enrollments_query.annotate(
                date=TruncDate('enrolled_at')
            ).values('date').annotate(
                count=Count('id')
            ).order_by('date')
            
            # Fill missing dates
            date_range_list = []
            current_date = start_date_obj.date()
            while current_date <= end_date_obj.date():
                date_range_list.append(current_date)
                current_date += timedelta(days=1)
            
            enrollment_dict = {item['date']: item for item in daily_data}
            
            # Get real earnings data for each date
            daily_enrollments = []
            for date in date_range_list:
                enrollment_count = enrollment_dict.get(date, {}).get('count', 0)
                
                # Get real earnings for this date
                real_earnings = InstructorEarning.objects.filter(
                    instructor=request.user,
                    date_earned=date
                ).aggregate(total_earnings=Sum('amount'))['total_earnings'] or 0
                
                daily_enrollments.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'count': enrollment_count,
                    'revenue': float(real_earnings)
                })
            
            weekly_enrollments = []
            monthly_enrollments = []
            
        elif timeframe == 'weekly':
            weekly_data = enrollments_query.annotate(
                week=TruncWeek('enrolled_at')
            ).values('week').annotate(
                count=Count('id')
            ).order_by('week')
            
            weekly_enrollments = []
            for i, item in enumerate(weekly_data):
                # Get real earnings for this week
                week_start = item['week']
                week_end = week_start + timedelta(weeks=1)
                
                real_earnings = InstructorEarning.objects.filter(
                    instructor=request.user,
                    date_earned__gte=week_start,
                    date_earned__lt=week_end
                ).aggregate(total_earnings=Sum('amount'))['total_earnings'] or 0
                
                weekly_enrollments.append({
                    'week': f"Week {i+1}",
                    'count': item['count'],
                    'revenue': float(real_earnings)
                })
            
            daily_enrollments = []
            monthly_enrollments = []
            
        else:  # monthly
            monthly_data = enrollments_query.annotate(
                month=TruncMonth('enrolled_at')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')
            
            monthly_enrollments = []
            for item in monthly_data:
                # Get real earnings for this month
                month_start = item['month']
                if month_start.month == 12:
                    next_month = month_start.replace(year=month_start.year + 1, month=1)
                else:
                    next_month = month_start.replace(month=month_start.month + 1)
                
                real_earnings = InstructorEarning.objects.filter(
                    instructor=request.user,
                    date_earned__gte=month_start,
                    date_earned__lt=next_month
                ).aggregate(total_earnings=Sum('amount'))['total_earnings'] or 0
                
                monthly_enrollments.append({
                    'month': item['month'].strftime('%B'),
                    'count': item['count'],
                    'revenue': float(real_earnings)
                })
            
            daily_enrollments = []
            weekly_enrollments = []

        # Course enrollment distribution
        course_enrollments = enrollments_query.values('course__title').annotate(
            enrollments=Count('id'),
            revenue=Sum('course__price')
        ).order_by('-enrollments')[:10]

        # Use real earnings data if available
        from .models import InstructorEarning
        
        course_enrollment_data = []
        for item in course_enrollments:
            course_title = item['course__title']
            
            # Get real earnings for this course
            real_earnings = InstructorEarning.objects.filter(
                instructor=request.user,
                course__title=course_title
            ).aggregate(total_earnings=Sum('amount'))['total_earnings'] or 0
            
            course_enrollment_data.append({
                'course': course_title,
                'enrollments': item['enrollments'],
                'revenue': float(real_earnings)
            })

        # Enrollment trends (quarterly growth)
        quarterly_data = enrollments_query.annotate(
            quarter=TruncQuarter('enrolled_at')
        ).values('quarter').annotate(
            count=Count('id')
        ).order_by('quarter')

        enrollment_trends = []
        for i, item in enumerate(quarterly_data):
            if i > 0:
                prev_count = quarterly_data[i-1]['count']
                growth = ((item['count'] - prev_count) / prev_count * 100) if prev_count > 0 else 0
                trend = 'up' if growth > 0 else 'down'
            else:
                growth = 0
                trend = 'up'
            
            enrollment_trends.append({
                'period': f"Q{(i % 4) + 1}",
                'growth': round(growth, 1),
                'trend': trend
            })

        # Peak enrollment times (hourly distribution)
        peak_times = enrollments_query.annotate(
            hour=ExtractHour('enrolled_at')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('-count')[:6]

        peak_enrollment_times = [
            {
                'hour': f"{item['hour']} AM" if item['hour'] < 12 else f"{item['hour'] - 12} PM",
                'count': item['count']
            }
            for item in peak_times
        ]

        # Mock conversion rates (since we don't have traffic data)
        conversion_rates = [
            {'source': 'Organic Search', 'rate': 12.5, 'visitors': 1200},
            {'source': 'Social Media', 'rate': 8.3, 'visitors': 800},
            {'source': 'Email Marketing', 'rate': 15.2, 'visitors': 500},
            {'source': 'Direct Traffic', 'rate': 6.8, 'visitors': 300}
        ]

        return Response({
            'dailyEnrollments': daily_enrollments,
            'weeklyEnrollments': weekly_enrollments,
            'monthlyEnrollments': monthly_enrollments,
            'courseEnrollments': course_enrollment_data,
            'enrollmentTrends': enrollment_trends,
            'peakEnrollmentTimes': peak_enrollment_times,
            'conversionRates': conversion_rates
        })


class CompletionAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get query parameters
        date_range = int(request.GET.get('date_range', 30))
        course = request.GET.get('course', 'all')
        timeframe = request.GET.get('timeframe', 'weekly')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        # Calculate date range
        end_date_obj = timezone.now()
        if end_date:
            end_date_obj = timezone.datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        
        start_date_obj = end_date_obj - timedelta(days=date_range)
        if start_date:
            start_date_obj = timezone.datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)

        # Check if user has any courses
        user_courses = Course.objects.filter(instructor=request.user)
        if not user_courses.exists():
            # Return mock data if no courses exist
            return Response({
                'courseCompletionRates': [
                    {'course': 'React Development', 'completion_rate': 78, 'total_students': 120, 'completed': 94},
                    {'course': 'Python Programming', 'completion_rate': 85, 'total_students': 95, 'completed': 81},
                    {'course': 'Web Design', 'completion_rate': 72, 'total_students': 88, 'completed': 63},
                    {'course': 'Data Science', 'completion_rate': 68, 'total_students': 75, 'completed': 51}
                ],
                'lessonCompletionRates': [
                    {'lesson': 'Introduction', 'completion_rate': 95, 'students': 120},
                    {'lesson': 'Basic Concepts', 'completion_rate': 88, 'students': 114},
                    {'lesson': 'Advanced Topics', 'completion_rate': 76, 'students': 100},
                    {'lesson': 'Final Project', 'completion_rate': 65, 'students': 85}
                ],
                'completionTrends': [
                    {'period': 'Week 1', 'rate': 25, 'trend': 'up'},
                    {'period': 'Week 2', 'rate': 45, 'trend': 'up'},
                    {'period': 'Week 3', 'rate': 62, 'trend': 'up'},
                    {'period': 'Week 4', 'rate': 78, 'trend': 'up'},
                    {'period': 'Week 5', 'rate': 85, 'trend': 'up'},
                    {'period': 'Week 6', 'rate': 92, 'trend': 'up'}
                ],
                'studentProgress': [
                    {'student': 'John Doe', 'progress': 85, 'completed_lessons': 17, 'total_lessons': 20},
                    {'student': 'Jane Smith', 'progress': 92, 'completed_lessons': 18, 'total_lessons': 20},
                    {'student': 'Mike Johnson', 'progress': 78, 'completed_lessons': 15, 'total_lessons': 20},
                    {'student': 'Sarah Wilson', 'progress': 95, 'completed_lessons': 19, 'total_lessons': 20}
                ],
                'completionByCategory': [
                    {'category': 'Programming', 'completion_rate': 82, 'students': 150},
                    {'category': 'Design', 'completion_rate': 75, 'students': 120},
                    {'category': 'Business', 'completion_rate': 88, 'students': 95},
                    {'category': 'Marketing', 'completion_rate': 70, 'students': 85}
                ],
                'averageCompletionTime': [
                    {'course': 'React Development', 'avg_days': 45, 'avg_hours': 120},
                    {'course': 'Python Programming', 'avg_days': 38, 'avg_hours': 95},
                    {'course': 'Web Design', 'avg_days': 52, 'avg_hours': 140},
                    {'course': 'Data Science', 'avg_days': 60, 'avg_hours': 180}
                ],
                'dropoutRates': [
                    {'week': 'Week 1', 'dropout_rate': 15, 'students_dropped': 18},
                    {'week': 'Week 2', 'dropout_rate': 8, 'students_dropped': 10},
                    {'week': 'Week 3', 'dropout_rate': 5, 'students_dropped': 6},
                    {'week': 'Week 4', 'dropout_rate': 3, 'students_dropped': 4}
                ],
                'certificationRates': [
                    {'course': 'React Development', 'certification_rate': 65, 'certificates_issued': 61},
                    {'course': 'Python Programming', 'certification_rate': 72, 'certificates_issued': 58},
                    {'course': 'Web Design', 'certification_rate': 58, 'certificates_issued': 37},
                    {'course': 'Data Science', 'certification_rate': 55, 'certificates_issued': 28}
                ]
            })

        # Filter enrollments and progress
        enrollments_query = Enrollment.objects.filter(
            course__instructor=request.user,
            is_enrolled=True
        )
        
        if course != 'all':
            enrollments_query = enrollments_query.filter(course__title__icontains=course)

        # Check if there are any enrollments
        if not enrollments_query.exists():
            # Return mock data if no enrollments exist
            return Response({
                'courseCompletionRates': [
                    {'course': course.title, 'completion_rate': 0, 'total_students': 0, 'completed': 0}
                    for course in user_courses[:5]
                ],
                'lessonCompletionRates': [],
                'completionTrends': [
                    {'period': f'Week {i+1}', 'rate': 0, 'trend': 'up'}
                    for i in range(6)
                ],
                'studentProgress': [],
                'completionByCategory': [
                    {'category': 'Programming', 'completion_rate': 0, 'students': 0},
                    {'category': 'Design', 'completion_rate': 0, 'students': 0},
                    {'category': 'Business', 'completion_rate': 0, 'students': 0},
                    {'category': 'Marketing', 'completion_rate': 0, 'students': 0}
                ],
                'averageCompletionTime': [
                    {'course': course.title, 'avg_days': 0, 'avg_hours': 0}
                    for course in user_courses[:5]
                ],
                'dropoutRates': [
                    {'week': f'Week {i+1}', 'dropout_rate': 0, 'students_dropped': 0}
                    for i in range(4)
                ],
                'certificationRates': [
                    {'course': course.title, 'certification_rate': 0, 'certificates_issued': 0}
                    for course in user_courses[:5]
                ]
            })

        # Course completion rates
        course_completion_data = []
        for enrollment in enrollments_query.select_related('course', 'student'):
            total_lessons = enrollment.course.lessons.count()
            completed_lessons = LessonProgress.objects.filter(
                lesson__course=enrollment.course,
                student=enrollment.student,
                completed=True
            ).count()
            
            completion_rate = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
            
            course_completion_data.append({
                'course': enrollment.course.title,
                'completion_rate': round(completion_rate, 1),
                'total_students': 1,
                'completed': 1 if completion_rate >= 100 else 0
            })

        # Aggregate by course
        course_completion_rates = []
        course_dict = {}
        for item in course_completion_data:
            course_name = item['course']
            if course_name not in course_dict:
                course_dict[course_name] = {
                    'course': course_name,
                    'completion_rate': 0,
                    'total_students': 0,
                    'completed': 0
                }
            course_dict[course_name]['total_students'] += item['total_students']
            course_dict[course_name]['completed'] += item['completed']
        
        for course_data in course_dict.values():
            if course_data['total_students'] > 0:
                course_data['completion_rate'] = round(
                    (course_data['completed'] / course_data['total_students']) * 100, 1
                )
            course_completion_rates.append(course_data)

        # Completion trends over time
        completion_trends = []
        for i in range(6):
            week_start = start_date_obj + timedelta(weeks=i)
            week_end = week_start + timedelta(weeks=1)
            
            week_enrollments = enrollments_query.filter(
                enrolled_at__range=(week_start, week_end)
            )
            
            total_students = week_enrollments.count()
            completed_students = 0
            
            for enrollment in week_enrollments:
                total_lessons = enrollment.course.lessons.count()
                completed_lessons = LessonProgress.objects.filter(
                    lesson__course=enrollment.course,
                    student=enrollment.student,
                    completed=True
                ).count()
                
                if total_lessons > 0 and (completed_lessons / total_lessons) >= 1:
                    completed_students += 1
            
            completion_rate = (completed_students / total_students * 100) if total_students > 0 else 0
            
            completion_trends.append({
                'period': f'Week {i+1}',
                'rate': round(completion_rate, 1),
                'trend': 'up'
            })

        # Student progress
        student_progress = []
        for enrollment in enrollments_query.select_related('course', 'student')[:10]:
            total_lessons = enrollment.course.lessons.count()
            completed_lessons = LessonProgress.objects.filter(
                lesson__course=enrollment.course,
                student=enrollment.student,
                completed=True
            ).count()
            
            progress = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
            
            student_progress.append({
                'student': enrollment.student.username,
                'progress': round(progress, 1),
                'completed_lessons': completed_lessons,
                'total_lessons': total_lessons
            })

        # Completion by category (mock data)
        completion_by_category = [
            {'category': 'Programming', 'completion_rate': 82, 'students': 150},
            {'category': 'Design', 'completion_rate': 75, 'students': 120},
            {'category': 'Business', 'completion_rate': 88, 'students': 95},
            {'category': 'Marketing', 'completion_rate': 70, 'students': 85}
        ]

        # Average completion time
        average_completion_time = []
        for enrollment in enrollments_query.select_related('course')[:5]:
            first_progress = LessonProgress.objects.filter(
                lesson__course=enrollment.course,
                student=enrollment.student
            ).order_by('completed_at').first()
            
            last_progress = LessonProgress.objects.filter(
                lesson__course=enrollment.course,
                student=enrollment.student,
                completed=True
            ).order_by('-completed_at').first()
            
            if first_progress and last_progress:
                days_diff = (last_progress.completed_at - first_progress.completed_at).days
                avg_days = max(1, days_diff)
            else:
                avg_days = 45  # Default
            
            average_completion_time.append({
                'course': enrollment.course.title,
                'avg_days': avg_days,
                'avg_hours': avg_days * 2.5  # Estimate
            })

        # Dropout rates
        dropout_rates = []
        for i in range(4):
            week_start = start_date_obj + timedelta(weeks=i)
            week_end = week_start + timedelta(weeks=1)
            
            week_enrollments = enrollments_query.filter(
                enrolled_at__range=(week_start, week_end)
            )
            
            total_students = week_enrollments.count()
            dropped_students = 0
            
            for enrollment in week_enrollments:
                # Check if student has been inactive for more than 7 days
                last_activity = LessonProgress.objects.filter(
                    lesson__course=enrollment.course,
                    student=enrollment.student
                ).order_by('-completed_at').first()
                
                if last_activity:
                    days_inactive = (timezone.now() - last_activity.completed_at).days
                    if days_inactive > 7:
                        dropped_students += 1
            
            dropout_rate = (dropped_students / total_students * 100) if total_students > 0 else 0
            
            dropout_rates.append({
                'week': f'Week {i+1}',
                'dropout_rate': round(dropout_rate, 1),
                'students_dropped': dropped_students
            })

        # Certification rates
        certification_rates = []
        for enrollment in enrollments_query.select_related('course')[:5]:
            total_lessons = enrollment.course.lessons.count()
            completed_lessons = LessonProgress.objects.filter(
                lesson__course=enrollment.course,
                student=enrollment.student,
                completed=True
            ).count()
            
            if total_lessons > 0 and (completed_lessons / total_lessons) >= 0.8:  # 80% threshold
                certification_rate = 65  # Mock certification rate
                certificates_issued = 1
            else:
                certification_rate = 0
                certificates_issued = 0
            
            certification_rates.append({
                'course': enrollment.course.title,
                'certification_rate': certification_rate,
                'certificates_issued': certificates_issued
            })

        return Response({
            'courseCompletionRates': course_completion_rates,
            'lessonCompletionRates': [],  # Could be implemented similarly
            'completionTrends': completion_trends,
            'studentProgress': student_progress,
            'completionByCategory': completion_by_category,
            'averageCompletionTime': average_completion_time,
            'dropoutRates': dropout_rates,
            'certificationRates': certification_rates
        })


class PerformanceAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get query parameters
        date_range = int(request.GET.get('date_range', 30))
        course = request.GET.get('course', 'all')
        timeframe = request.GET.get('timeframe', 'weekly')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        # Calculate date range
        end_date_obj = timezone.now()
        if end_date:
            end_date_obj = timezone.datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        
        start_date_obj = end_date_obj - timedelta(days=date_range)
        if start_date:
            start_date_obj = timezone.datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)

        # Check if user has any courses
        user_courses = Course.objects.filter(instructor=request.user)
        if not user_courses.exists():
            # Return mock data if no courses exist
            return Response({
                'studentScores': [
                    {'student': 'John Doe', 'course': 'React Development', 'score': 92, 'grade': 'A', 'assignments': 15, 'quizzes': 8},
                    {'student': 'Jane Smith', 'course': 'Python Programming', 'score': 88, 'grade': 'B+', 'assignments': 12, 'quizzes': 6},
                    {'student': 'Mike Johnson', 'course': 'Web Design', 'score': 95, 'grade': 'A+', 'assignments': 18, 'quizzes': 10},
                    {'student': 'Sarah Wilson', 'course': 'Data Science', 'score': 85, 'grade': 'B', 'assignments': 14, 'quizzes': 7}
                ],
                'performanceTrends': [
                    {'week': 'Week 1', 'avg_score': 75, 'trend': 'up'},
                    {'week': 'Week 2', 'avg_score': 78, 'trend': 'up'},
                    {'week': 'Week 3', 'avg_score': 82, 'trend': 'up'},
                    {'week': 'Week 4', 'avg_score': 85, 'trend': 'up'},
                    {'week': 'Week 5', 'avg_score': 88, 'trend': 'up'},
                    {'week': 'Week 6', 'avg_score': 91, 'trend': 'up'}
                ],
                'gradeDistribution': [
                    {'grade': 'A+', 'count': 25, 'percentage': 15},
                    {'grade': 'A', 'count': 45, 'percentage': 27},
                    {'grade': 'B+', 'count': 38, 'percentage': 23},
                    {'grade': 'B', 'count': 32, 'percentage': 19},
                    {'grade': 'C+', 'count': 18, 'percentage': 11},
                    {'grade': 'C', 'count': 8, 'percentage': 5}
                ],
                'topPerformers': [
                    {'student': 'Mike Johnson', 'score': 95, 'course': 'Web Design', 'improvement': 12},
                    {'student': 'John Doe', 'score': 92, 'course': 'React Development', 'improvement': 8},
                    {'student': 'Jane Smith', 'score': 88, 'course': 'Python Programming', 'improvement': 6}
                ],
                'performanceByCourse': [
                    {'course': 'React Development', 'avg_score': 85, 'total_students': 45, 'high_performers': 12},
                    {'course': 'Python Programming', 'avg_score': 88, 'total_students': 38, 'high_performers': 15},
                    {'course': 'Web Design', 'avg_score': 82, 'total_students': 32, 'high_performers': 8},
                    {'course': 'Data Science', 'avg_score': 79, 'total_students': 28, 'high_performers': 6}
                ],
                'learningProgress': [
                    {'student': 'John Doe', 'progress': 85, 'time_spent': 120, 'assignments_completed': 15},
                    {'student': 'Jane Smith', 'progress': 92, 'time_spent': 95, 'assignments_completed': 12},
                    {'student': 'Mike Johnson', 'progress': 78, 'time_spent': 140, 'assignments_completed': 18}
                ],
                'assessmentResults': [
                    {'assessment': 'Midterm Exam', 'avg_score': 82, 'pass_rate': 85, 'total_students': 120},
                    {'assessment': 'Final Project', 'avg_score': 88, 'pass_rate': 92, 'total_students': 115},
                    {'assessment': 'Quiz 1', 'avg_score': 75, 'pass_rate': 78, 'total_students': 125},
                    {'assessment': 'Quiz 2', 'avg_score': 79, 'pass_rate': 82, 'total_students': 122}
                ],
                'engagementMetrics': [
                    {'metric': 'Discussion Participation', 'score': 85, 'trend': 'up'},
                    {'metric': 'Assignment Submission', 'score': 92, 'trend': 'up'},
                    {'metric': 'Video Watch Time', 'score': 78, 'trend': 'stable'},
                    {'metric': 'Peer Reviews', 'score': 88, 'trend': 'up'}
                ]
            })

        # Filter enrollments
        enrollments_query = Enrollment.objects.filter(
            course__instructor=request.user,
            is_enrolled=True
        )
        
        if course != 'all':
            enrollments_query = enrollments_query.filter(course__title__icontains=course)

        # Check if there are any enrollments
        if not enrollments_query.exists():
            # Return mock data if no enrollments exist
            return Response({
                'studentScores': [],
                'performanceTrends': [
                    {'week': f'Week {i+1}', 'avg_score': 0, 'trend': 'up'}
                    for i in range(6)
                ],
                'gradeDistribution': [
                    {'grade': 'A+', 'count': 0, 'percentage': 0},
                    {'grade': 'A', 'count': 0, 'percentage': 0},
                    {'grade': 'B+', 'count': 0, 'percentage': 0},
                    {'grade': 'B', 'count': 0, 'percentage': 0},
                    {'grade': 'C+', 'count': 0, 'percentage': 0},
                    {'grade': 'C', 'count': 0, 'percentage': 0}
                ],
                'topPerformers': [],
                'performanceByCourse': [
                    {'course': course.title, 'avg_score': 0, 'total_students': 0, 'high_performers': 0}
                    for course in user_courses[:5]
                ],
                'learningProgress': [],
                'assessmentResults': [
                    {'assessment': 'Midterm Exam', 'avg_score': 0, 'pass_rate': 0, 'total_students': 0},
                    {'assessment': 'Final Project', 'avg_score': 0, 'pass_rate': 0, 'total_students': 0},
                    {'assessment': 'Quiz 1', 'avg_score': 0, 'pass_rate': 0, 'total_students': 0},
                    {'assessment': 'Quiz 2', 'avg_score': 0, 'pass_rate': 0, 'total_students': 0}
                ],
                'engagementMetrics': [
                    {'metric': 'Discussion Participation', 'score': 0, 'trend': 'up'},
                    {'metric': 'Assignment Submission', 'score': 0, 'trend': 'up'},
                    {'metric': 'Video Watch Time', 'score': 0, 'trend': 'stable'},
                    {'metric': 'Peer Reviews', 'score': 0, 'trend': 'up'}
                ]
            })

        # Student scores (based on lesson completion and activity)
        student_scores = []
        for enrollment in enrollments_query.select_related('course', 'student')[:10]:
            total_lessons = enrollment.course.lessons.count()
            completed_lessons = LessonProgress.objects.filter(
                lesson__course=enrollment.course,
                student=enrollment.student,
                completed=True
            ).count()
            
            # Calculate score based on completion and activity
            completion_score = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
            
            # Activity score based on recent activity
            recent_activity = Activity.objects.filter(
                user=enrollment.student,
                activity_type__in=['lesson_completed', 'enrollment'],
                timestamp__gte=timezone.now() - timedelta(days=30)
            ).count()
            
            activity_score = min(20, recent_activity * 2)  # Max 20 points for activity
            
            total_score = min(100, completion_score + activity_score)
            
            # Determine grade
            if total_score >= 95:
                grade = 'A+'
            elif total_score >= 90:
                grade = 'A'
            elif total_score >= 85:
                grade = 'B+'
            elif total_score >= 80:
                grade = 'B'
            elif total_score >= 75:
                grade = 'C+'
            else:
                grade = 'C'
            
            student_scores.append({
                'student': enrollment.student.username,
                'course': enrollment.course.title,
                'score': round(total_score, 1),
                'grade': grade,
                'assignments': completed_lessons,
                'quizzes': min(completed_lessons, 10)  # Mock quiz count
            })

        # Performance trends over time
        performance_trends = []
        for i in range(6):
            week_start = start_date_obj + timedelta(weeks=i)
            week_end = week_start + timedelta(weeks=1)
            
            week_enrollments = enrollments_query.filter(
                enrolled_at__range=(week_start, week_end)
            )
            
            week_scores = []
            for enrollment in week_enrollments:
                total_lessons = enrollment.course.lessons.count()
                completed_lessons = LessonProgress.objects.filter(
                    lesson__course=enrollment.course,
                    student=enrollment.student,
                    completed=True
                ).count()
                
                completion_score = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
                week_scores.append(completion_score)
            
            avg_score = sum(week_scores) / len(week_scores) if week_scores else 0
            
            performance_trends.append({
                'week': f'Week {i+1}',
                'avg_score': round(avg_score, 1),
                'trend': 'up'
            })

        # Grade distribution
        grade_counts = {}
        for score_data in student_scores:
            grade = score_data['grade']
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        grade_distribution = [
            {'grade': grade, 'count': count, 'percentage': round(count / len(student_scores) * 100, 1)}
            for grade, count in grade_counts.items()
        ]

        # Top performers
        top_performers = sorted(student_scores, key=lambda x: x['score'], reverse=True)[:4]
        top_performers_data = [
            {
                'student': item['student'],
                'score': item['score'],
                'course': item['course'],
                'improvement': round(item['score'] * 0.1, 1)  # Mock improvement
            }
            for item in top_performers
        ]

        # Performance by course
        course_performance = {}
        for score_data in student_scores:
            course = score_data['course']
            if course not in course_performance:
                course_performance[course] = {
                    'course': course,
                    'scores': [],
                    'total_students': 0,
                    'high_performers': 0
                }
            course_performance[course]['scores'].append(score_data['score'])
            course_performance[course]['total_students'] += 1
            if score_data['score'] >= 90:
                course_performance[course]['high_performers'] += 1
        
        performance_by_course = [
            {
                'course': data['course'],
                'avg_score': round(sum(data['scores']) / len(data['scores']), 1),
                'total_students': data['total_students'],
                'high_performers': data['high_performers']
            }
            for data in course_performance.values()
        ]

        # Learning progress
        learning_progress = []
        for enrollment in enrollments_query.select_related('course', 'student')[:5]:
            total_lessons = enrollment.course.lessons.count()
            completed_lessons = LessonProgress.objects.filter(
                lesson__course=enrollment.course,
                student=enrollment.student,
                completed=True
            ).count()
            
            progress = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
            
            learning_progress.append({
                'student': enrollment.student.username,
                'progress': round(progress, 1),
                'time_spent': completed_lessons * 2,  # Mock hours
                'assignments_completed': completed_lessons
            })

        # Assessment results (mock data)
        assessment_results = [
            {'assessment': 'Midterm Exam', 'avg_score': 82, 'pass_rate': 85, 'total_students': 120},
            {'assessment': 'Final Project', 'avg_score': 88, 'pass_rate': 92, 'total_students': 115},
            {'assessment': 'Quiz 1', 'avg_score': 75, 'pass_rate': 78, 'total_students': 125},
            {'assessment': 'Quiz 2', 'avg_score': 79, 'pass_rate': 82, 'total_students': 122}
        ]

        # Engagement metrics (mock data)
        engagement_metrics = [
            {'metric': 'Discussion Participation', 'score': 85, 'trend': 'up'},
            {'metric': 'Assignment Submission', 'score': 92, 'trend': 'up'},
            {'metric': 'Video Watch Time', 'score': 78, 'trend': 'stable'},
            {'metric': 'Peer Reviews', 'score': 88, 'trend': 'up'}
        ]

        return Response({
            'studentScores': student_scores,
            'performanceTrends': performance_trends,
            'gradeDistribution': grade_distribution,
            'topPerformers': top_performers_data,
            'performanceByCourse': performance_by_course,
            'learningProgress': learning_progress,
            'assessmentResults': assessment_results,
            'engagementMetrics': engagement_metrics
        })


class EarningsAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get query parameters
        date_range = int(request.GET.get('date_range', 30))
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        # Calculate date range
        end_date_obj = timezone.now()
        if end_date:
            end_date_obj = timezone.datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        
        start_date_obj = end_date_obj - timedelta(days=date_range)
        if start_date:
            start_date_obj = timezone.datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)

        from .models import InstructorEarning, InstructorPayout

        # Check if user has any earnings
        user_earnings = InstructorEarning.objects.filter(instructor=request.user)
        if not user_earnings.exists():
            # Return mock data if no earnings exist
            return Response({
                'totalEarnings': 0,
                'totalPayouts': 0,
                'pendingPayouts': 0,
                'earningsByCourse': [],
                'earningsTrend': [],
                'payoutHistory': [],
                'monthlyEarnings': [
                    {'month': 'January', 'earnings': 0, 'payouts': 0},
                    {'month': 'February', 'earnings': 0, 'payouts': 0},
                    {'month': 'March', 'earnings': 0, 'payouts': 0},
                    {'month': 'April', 'earnings': 0, 'payouts': 0}
                ],
                'recentTransactions': []
            })

        # Get earnings data
        earnings_in_period = user_earnings.filter(
            date_earned__range=(start_date_obj.date(), end_date_obj.date())
        )
        
        total_earnings = earnings_in_period.aggregate(
            total=Sum('amount')
        )['total'] or 0

        # Get payout data
        payouts_in_period = InstructorPayout.objects.filter(
            instructor=request.user,
            date__range=(start_date_obj.date(), end_date_obj.date())
        )
        
        total_payouts = payouts_in_period.aggregate(
            total=Sum('amount')
        )['total'] or 0

        pending_payouts = InstructorPayout.objects.filter(
            instructor=request.user,
            status='pending'
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0

        # Earnings by course
        earnings_by_course = earnings_in_period.values('course__title').annotate(
            total_earnings=Sum('amount'),
            enrollment_count=Count('id')
        ).order_by('-total_earnings')[:10]

        earnings_by_course_data = [
            {
                'course': item['course__title'],
                'earnings': float(item['total_earnings']),
                'enrollments': item['enrollment_count']
            }
            for item in earnings_by_course
        ]

        # Earnings trend over time
        earnings_trend = earnings_in_period.annotate(
            date=TruncDate('date_earned')
        ).values('date').annotate(
            daily_earnings=Sum('amount')
        ).order_by('date')

        # Fill missing dates
        date_range_list = []
        current_date = start_date_obj.date()
        while current_date <= end_date_obj.date():
            date_range_list.append(current_date)
            current_date += timedelta(days=1)
        
        earnings_dict = {item['date']: item['daily_earnings'] for item in earnings_trend}
        
        earnings_trend_data = [
            {
                'date': date.strftime('%Y-%m-%d'),
                'earnings': float(earnings_dict.get(date, 0))
            }
            for date in date_range_list
        ]

        # Payout history
        payout_history = payouts_in_period.order_by('-date')[:10]
        
        payout_history_data = [
            {
                'date': payout.date.strftime('%Y-%m-%d'),
                'amount': float(payout.amount),
                'status': payout.status,
                'method': payout.method
            }
            for payout in payout_history
        ]

        # Monthly earnings and payouts
        monthly_earnings = earnings_in_period.annotate(
            month=TruncMonth('date_earned')
        ).values('month').annotate(
            monthly_earnings=Sum('amount')
        ).order_by('month')

        monthly_payouts = payouts_in_period.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            monthly_payouts=Sum('amount')
        ).order_by('month')

        earnings_dict = {item['month']: item['monthly_earnings'] for item in monthly_earnings}
        payouts_dict = {item['month']: item['monthly_payouts'] for item in monthly_payouts}

        monthly_data = []
        for month in earnings_dict.keys():
            monthly_data.append({
                'month': month.strftime('%B'),
                'earnings': float(earnings_dict.get(month, 0)),
                'payouts': float(payouts_dict.get(month, 0))
            })

        # Recent transactions
        recent_earnings = earnings_in_period.order_by('-date_earned')[:5]
        recent_payouts = payouts_in_period.order_by('-date')[:5]
        
        recent_transactions = []
        
        for earning in recent_earnings:
            recent_transactions.append({
                'date': earning.date_earned.strftime('%Y-%m-%d'),
                'type': 'earning',
                'amount': float(earning.amount),
                'description': f"Earning from {earning.course.title}",
                'status': 'completed'
            })
        
        for payout in recent_payouts:
            recent_transactions.append({
                'date': payout.date.strftime('%Y-%m-%d'),
                'type': 'payout',
                'amount': float(payout.amount),
                'description': f"Payout via {payout.method}",
                'status': payout.status
            })
        
        # Sort by date (most recent first)
        recent_transactions.sort(key=lambda x: x['date'], reverse=True)
        recent_transactions = recent_transactions[:10]

        return Response({
            'totalEarnings': float(total_earnings),
            'totalPayouts': float(total_payouts),
            'pendingPayouts': float(pending_payouts),
            'earningsByCourse': earnings_by_course_data,
            'earningsTrend': earnings_trend_data,
            'payoutHistory': payout_history_data,
            'monthlyEarnings': monthly_data,
            'recentTransactions': recent_transactions
        })