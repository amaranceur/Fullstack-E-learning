from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils.timezone import now
from django.db.models import JSONField
class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('instructor', 'Instructor'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',  # <-- unique related_name
        blank=True,
        help_text=(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_set',  # <-- unique related_name
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )
class Profile(models.Model):
    USER_ROLES = (
        ('student', 'Student'),
        ('instructor', 'Instructor'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profiles/', default='profiles/default.jpg')
    member_since = models.DateField(default=now)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def courses_enrolled_count(self):
        return self.user.enrollments.count()  # assuming related_name="enrollments"

    @property
    def certificates_count(self):
        return self.user.certificates.count()  # assuming related_name="certificates"

class InstructorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='instructor_profile')
    profile_picture = models.ImageField(upload_to='instructor_profiles/', default='profiles/default.jpg')
    bio = models.TextField(blank=True, help_text="Instructor's biography and teaching philosophy")
    specialty = models.CharField(max_length=200, blank=True, help_text="Main area of expertise")
    
    # Social Media Links
    linkedin_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)
    website_url = models.URLField(blank=True, null=True)
    
    # Additional Info
    years_of_experience = models.PositiveIntegerField(default=0)
    education = models.TextField(blank=True, help_text="Educational background")
    certifications = models.TextField(blank=True, help_text="Professional certifications")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Instructor Profile"

    @property
    def total_courses(self):
        return self.user.instructed_courses.count()

    @property
    def total_students(self):
        return self.user.instructed_courses.aggregate(
            total_students=models.Count('enrollments')
        )['total_students'] or 0

    @property
    def average_rating(self):
        # You can implement rating logic here when you add ratings
        return 4.5  # Placeholder

class Activity(models.Model):
    ACTIVITY_TYPES = [
        ('enrollment', 'Enrollment'),
        ('certificate', 'Certificate Earned'),
        ('profile_update', 'Profile Update'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('lesson_completed', 'Lesson Completed'),
        ('lesson_uploaded', 'Lesson Uploaded'),
        ('announcement_created', 'Announcement Created'),
        ('announcement_updated', 'Announcement Updated'),
        ('announcement_deleted', 'Announcement Deleted'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES, default='other')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='instructed_courses')
    category = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='course_images/', null=True, blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    video_url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.course.title} - {self.title}"
class Enrollment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('declined', 'Declined'),
        ('accepted', 'Accepted'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)

    # Payment fields
    is_paid = models.BooleanField(default=False)
    is_enrolled =models.BooleanField(default=False)
    amount_paid = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )

    class Meta:
        unique_together = ('student', 'course')

    def save(self, *args, **kwargs):
        if self.course.price == 0:
            self.is_paid = True
            self.payment_status = 'accepted'
            self.amount_paid = 0.00
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.username} -> {self.course.title}"


class LessonProgress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'lesson')
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class CourseDetails(models.Model):
    course = models.OneToOneField('Course', on_delete=models.CASCADE, related_name='details')
    
    duration = models.CharField(max_length=20, blank=True)  # "8h 12m"
    level = models.CharField(max_length=50, default='Beginner')
    forma = models.CharField(max_length=50, default='Video')
    
    what_you_will_learn =models.JSONField(default=list)  # Store as \n-separated list
    requirements = models.JSONField(default=list)    
    curriculum = models.JSONField(default=list)
    def __str__(self):
        return f"Details for {self.course.title}"
class Certificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    issue_date = models.DateField(auto_now_add=True)
    certificate_file = models.FileField(upload_to='certificates/', null=True, blank=True)
    certificate_id = models.CharField(max_length=100, unique=True)
class Announcement(models.Model):
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='announcements')
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)  # optional scheduling
    is_published = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.title} - {self.course.name}"
class InstructorPayout(models.Model):
    instructor = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('paid', 'Paid')])
    method = models.CharField(max_length=50, default='paypal')
    invoice = models.FileField(upload_to='payout_invoices/', blank=True, null=True)

class InstructorEarning(models.Model):
    instructor = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(User, related_name='earnings_from', on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_earned = models.DateField(auto_now_add=True)
    is_included_in_payout = models.BooleanField(default=False)