from .models import User ,Profile, Course,CourseDetails,Enrollment,Lesson
from .models import InstructorProfile,LessonProgress,Comment,Certificate,Announcement
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import ValidationError
# users/serializers.py

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    role = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")
        role = attrs.get("role")

        data = super().validate(attrs)

        user = self.user
        if user.role != role:
            raise serializers.ValidationError("Invalid role for this user")

        data['role'] = user.role
        data['username'] = user.username
        return data

class AnnouncementSerializer(serializers.ModelSerializer):
    instructor_username = serializers.CharField(source='instructor.username', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'instructor', 'instructor_username', 'course', 'course_title',
            'title', 'message', 'created_at', 'scheduled_for', 'is_published'
        ]
        read_only_fields = ['id', 'created_at', 'instructor_username', 'course_title', 'instructor']

    def create(self, validated_data):
        # Set the instructor to the current user
        validated_data['instructor'] = self.context['request'].user
        return super().create(validated_data)

    def validate(self, attrs):
        # Ensure the instructor can only create announcements for their own courses
        course = attrs.get('course')
        if course and course.instructor != self.context['request'].user:
            raise serializers.ValidationError("You can only create announcements for your own courses.")
        return attrs

class AnnouncementListSerializer(serializers.ModelSerializer):
    instructor_username = serializers.CharField(source='instructor.username', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'instructor_username', 'course_title',
            'title', 'message', 'created_at', 'scheduled_for', 'is_published'
        ]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email","role"]
class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    email = serializers.EmailField(source='user.email')
    courses_enrolled_count = serializers.IntegerField(read_only=True)
    certificates_count = serializers.IntegerField(read_only=True)
    role = serializers.CharField(source='user.role')
    class Meta:
        model = Profile
        fields = [
            'username',
            'email',
            'profile_picture',
            'member_since',
            'courses_enrolled_count',
            'certificates_count',
            'role'
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user

        # Update user fields
        user.username = user_data.get('username', user.username)
        user.email = user_data.get('email', user.email)
        user.save()

        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance
class Register(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username", "email", "role",
             "password"
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise ValidationError({'password': e.messages})
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=validated_data.get('role', ''),
        )
        
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        # Optional: add validation like minimum length, special characters, etc.
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        return value

class CourseSerializer(serializers.ModelSerializer):
    instructor_username = serializers.CharField(source='instructor.username', read_only=True)
    instructor_profile_picture = serializers.SerializerMethodField()
    enrollments_count = serializers.SerializerMethodField()
    lessons_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'instructor', 'instructor_username', 'instructor_profile_picture', 'category', 'image', 'price', 'created_at', 'enrollments_count', 'lessons_count'
        ]
        read_only_fields = ['id', 'created_at', 'instructor_username', 'instructor_profile_picture', 'instructor']

    def get_instructor_profile_picture(self, obj):
        # First try to get instructor profile, then fall back to regular profile
        instructor_profile = getattr(obj.instructor, 'instructor_profile', None)
        if instructor_profile and instructor_profile.profile_picture:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(instructor_profile.profile_picture.url)
            return instructor_profile.profile_picture.url
        else:
            # Fallback to regular profile
            profile = getattr(obj.instructor, 'profile', None)
            if profile and profile.profile_picture:
                request = self.context.get('request')
                if request is not None:
                    return request.build_absolute_uri(profile.profile_picture.url)
                return profile.profile_picture.url
        return None

    def get_enrollments_count(self, obj):
        return obj.enrollments.count()

    def get_lessons_count(self, obj):
        return obj.lessons.count()
class CourseDetailsSerializer(serializers.ModelSerializer):
    course = CourseSerializer()
    instructor_bio = serializers.SerializerMethodField()
    class Meta:
        model = CourseDetails
        fields = ['id', 'course', 'duration', 'level', 'forma', 'what_you_will_learn', 'requirements', 'instructor_bio', 'curriculum']

    def get_instructor_bio(self, obj):
        """Get instructor bio from InstructorProfile, fallback to empty string"""
        instructor = obj.course.instructor
        try:
            instructor_profile = instructor.instructor_profile
            return instructor_profile.bio if instructor_profile.bio else ""
        except InstructorProfile.DoesNotExist:
            return ""

class InstructorProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    total_courses = serializers.IntegerField(read_only=True)
    total_students = serializers.IntegerField(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    
    class Meta:
        model = InstructorProfile
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'profile_picture', 'profile_picture_url', 'bio', 'specialty',
            'linkedin_url', 'twitter_url', 'github_url', 'youtube_url', 'website_url',
            'years_of_experience', 'education', 'certifications',
            'total_courses', 'total_students', 'average_rating',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                           'profile_picture_url', 'total_courses', 'total_students', 
                           'average_rating', 'created_at', 'updated_at']

    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None

    def update(self, instance, validated_data):
        # Update instructor profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class InstructorProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating instructor profile (excludes read-only fields)"""
    class Meta:
        model = InstructorProfile
        fields = [
            'profile_picture', 'bio', 'specialty',
            'linkedin_url', 'twitter_url', 'github_url', 'youtube_url', 'website_url',
            'years_of_experience', 'education', 'certifications'
        ]

    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None
class EnrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'amount_paid', 'payment_method', 'payment_status', 'is_enrolled']  # include new fields

    def validate(self, attrs):
        course = attrs['course']
        if course.price > 0:
            if not attrs.get('amount_paid') or not attrs.get('payment_method'):
                raise serializers.ValidationError('amount_paid and payment_method are required for paid courses.')
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        course = validated_data['course']
        if course.price == 0:
            enrollment = Enrollment.objects.create(
                student=user,
                course=course,
                is_paid=True,
                is_enrolled=True,
                payment_status='accepted',
                amount_paid=0.00,
                payment_method=None
            )
        else:
            enrollment = Enrollment.objects.create(
                student=user,
                course=course,
                is_paid=False,
                is_enrolled=False,
                payment_status='pending',
                amount_paid=validated_data['amount_paid'],
                payment_method=validated_data['payment_method']
            )
        return enrollment

    def to_representation(self, instance):
        return {
            'payment_status': instance.payment_status,
            'is_enrolled': instance.is_enrolled
        }

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'course', 'title', 'content', 'video_url', 'order']

class CourseWithDetailsSerializer(serializers.ModelSerializer):
    details = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = '__all__'  # or list the fields you want + 'details'

    def get_details(self, obj):
        try:
            return CourseDetailsSerializer(obj.details).data
        except CourseDetails.DoesNotExist:
            return None

class CertificateSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    certificate_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Certificate
        fields = [
            'id', 'user', 'user_username', 'course', 'course_title', 
            'issue_date', 'certificate_file', 'certificate_file_url', 'certificate_id'
        ]
        read_only_fields = ['id', 'issue_date', 'certificate_id']
    
    def get_certificate_file_url(self, obj):
        if obj.certificate_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.certificate_file.url)
            return obj.certificate_file.url
        return None
    
    def create(self, validated_data):
        # Generate unique certificate ID
        import uuid
        validated_data['certificate_id'] = str(uuid.uuid4())
        return super().create(validated_data)

