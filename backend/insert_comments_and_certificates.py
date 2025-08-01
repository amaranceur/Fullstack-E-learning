from django.contrib.auth import get_user_model
from django.utils import timezone
from app.models import Course, Enrollment, Comment, Certificate  # Replace `app` with your actual app name

User = get_user_model()

def insert_comments():
    print("Inserting comments...")
    comments_data = [
        {
            "user_id": 2,
            "course_id": 2,
            "content": "This course helped me understand Django fundamentals. Highly recommended!"
        },
        {
            "user_id": 2,
            "course_id": 4,
            "content": "Very practical course with good examples. Loved it!"
        }
    ]
    for data in comments_data:
        try:
            user = User.objects.get(id=data["user_id"])
            course = Course.objects.get(id=data["course_id"])
            if not Comment.objects.filter(user=user, course=course, content=data["content"]).exists():
                Comment.objects.create(user=user, course=course, content=data["content"])
                print(f"Comment added: {user.username} -> {course.title}")
        except Exception as e:
            print(f"Error inserting comment: {e}")

def insert_certificates():
    print("Inserting certificates...")
    enrollments = Enrollment.objects.filter(completed=True)
    for enrollment in enrollments:
        try:
            cert, created = Certificate.objects.get_or_create(
                user=enrollment.student,
                course=enrollment.course,
                defaults={"issued_at": timezone.now()}
            )
            if created:
                print(f"Certificate created for {enrollment.student.username} - {enrollment.course.title}")
        except Exception as e:
            print(f"Error creating certificate: {e}")

def main():
    insert_comments()
    insert_certificates()

main()
