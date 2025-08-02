import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from app.models import User, Course, InstructorEarning, InstructorPayout

def insert_earnings_data():
    print("Starting to insert earnings data...")
    
    # Get the first instructor (assuming there's at least one)
    try:
        instructor = User.objects.filter(role='instructor').first()
        if not instructor:
            print("No instructor found. Creating a test instructor...")
            instructor = User.objects.create_user(
                username='test_instructor',
                email='instructor@test.com',
                password='testpass123',
                role='instructor'
            )
            print(f"Created instructor: {instructor.username}")
    except Exception as e:
        print(f"Error getting instructor: {e}")
        return
    
    # Get courses for this instructor
    courses = Course.objects.filter(instructor=instructor)
    if not courses.exists():
        print("No courses found for instructor. Creating sample courses...")
        courses = [
            Course.objects.create(
                title='React Development',
                description='Learn React from scratch',
                instructor=instructor,
                category='Programming',
                price=Decimal('99.99')
            ),
            Course.objects.create(
                title='Python Programming',
                description='Master Python programming',
                instructor=instructor,
                category='Programming',
                price=Decimal('79.99')
            ),
            Course.objects.create(
                title='Web Design',
                description='Create beautiful websites',
                instructor=instructor,
                category='Design',
                price=Decimal('89.99')
            ),
            Course.objects.create(
                title='Data Science',
                description='Introduction to data science',
                instructor=instructor,
                category='Data',
                price=Decimal('129.99')
            )
        ]
        print(f"Created {len(courses)} courses")
    
    # Clear existing earnings and payouts for this instructor
    InstructorEarning.objects.filter(instructor=instructor).delete()
    InstructorPayout.objects.filter(instructor=instructor).delete()
    print("Cleared existing earnings and payouts data")
    
    # Generate earnings data for the last 30 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Sample earnings data
    earnings_data = [
        # React Development earnings
        {'course': courses[0], 'amount': Decimal('99.99'), 'date': end_date - timedelta(days=1)},
        {'course': courses[0], 'amount': Decimal('99.99'), 'date': end_date - timedelta(days=3)},
        {'course': courses[0], 'amount': Decimal('99.99'), 'date': end_date - timedelta(days=5)},
        {'course': courses[0], 'amount': Decimal('99.99'), 'date': end_date - timedelta(days=7)},
        {'course': courses[0], 'amount': Decimal('99.99'), 'date': end_date - timedelta(days=10)},
        {'course': courses[0], 'amount': Decimal('99.99'), 'date': end_date - timedelta(days=12)},
        {'course': courses[0], 'amount': Decimal('99.99'), 'date': end_date - timedelta(days=15)},
        {'course': courses[0], 'amount': Decimal('99.99'), 'date': end_date - timedelta(days=18)},
        {'course': courses[0], 'amount': Decimal('99.99'), 'date': end_date - timedelta(days=20)},
        {'course': courses[0], 'amount': Decimal('99.99'), 'date': end_date - timedelta(days=22)},
        
        # Python Programming earnings
        {'course': courses[1], 'amount': Decimal('79.99'), 'date': end_date - timedelta(days=2)},
        {'course': courses[1], 'amount': Decimal('79.99'), 'date': end_date - timedelta(days=4)},
        {'course': courses[1], 'amount': Decimal('79.99'), 'date': end_date - timedelta(days=6)},
        {'course': courses[1], 'amount': Decimal('79.99'), 'date': end_date - timedelta(days=8)},
        {'course': courses[1], 'amount': Decimal('79.99'), 'date': end_date - timedelta(days=11)},
        {'course': courses[1], 'amount': Decimal('79.99'), 'date': end_date - timedelta(days=13)},
        {'course': courses[1], 'amount': Decimal('79.99'), 'date': end_date - timedelta(days=16)},
        {'course': courses[1], 'amount': Decimal('79.99'), 'date': end_date - timedelta(days=19)},
        {'course': courses[1], 'amount': Decimal('79.99'), 'date': end_date - timedelta(days=21)},
        {'course': courses[1], 'amount': Decimal('79.99'), 'date': end_date - timedelta(days=23)},
        
        # Web Design earnings
        {'course': courses[2], 'amount': Decimal('89.99'), 'date': end_date - timedelta(days=1)},
        {'course': courses[2], 'amount': Decimal('89.99'), 'date': end_date - timedelta(days=4)},
        {'course': courses[2], 'amount': Decimal('89.99'), 'date': end_date - timedelta(days=7)},
        {'course': courses[2], 'amount': Decimal('89.99'), 'date': end_date - timedelta(days=10)},
        {'course': courses[2], 'amount': Decimal('89.99'), 'date': end_date - timedelta(days=13)},
        {'course': courses[2], 'amount': Decimal('89.99'), 'date': end_date - timedelta(days=16)},
        {'course': courses[2], 'amount': Decimal('89.99'), 'date': end_date - timedelta(days=19)},
        {'course': courses[2], 'amount': Decimal('89.99'), 'date': end_date - timedelta(days=22)},
        {'course': courses[2], 'amount': Decimal('89.99'), 'date': end_date - timedelta(days=25)},
        
        # Data Science earnings
        {'course': courses[3], 'amount': Decimal('129.99'), 'date': end_date - timedelta(days=3)},
        {'course': courses[3], 'amount': Decimal('129.99'), 'date': end_date - timedelta(days=6)},
        {'course': courses[3], 'amount': Decimal('129.99'), 'date': end_date - timedelta(days=9)},
        {'course': courses[3], 'amount': Decimal('129.99'), 'date': end_date - timedelta(days=12)},
        {'course': courses[3], 'amount': Decimal('129.99'), 'date': end_date - timedelta(days=15)},
        {'course': courses[3], 'amount': Decimal('129.99'), 'date': end_date - timedelta(days=18)},
        {'course': courses[3], 'amount': Decimal('129.99'), 'date': end_date - timedelta(days=21)},
        {'course': courses[3], 'amount': Decimal('129.99'), 'date': end_date - timedelta(days=24)},
        {'course': courses[3], 'amount': Decimal('129.99'), 'date': end_date - timedelta(days=27)},
    ]
    
    # Create earnings records
    earnings_created = []
    for earning_data in earnings_data:
        earning = InstructorEarning.objects.create(
            instructor=instructor,
            course=earning_data['course'],
            student=None,  # We don't have specific students for this demo
            amount=earning_data['amount'],
            date_earned=earning_data['date']
        )
        earnings_created.append(earning)
    
    print(f"Created {len(earnings_created)} earnings records")
    
    # Generate payout data
    payouts_data = [
        {'amount': Decimal('2500.00'), 'date': end_date - timedelta(days=5), 'status': 'paid', 'method': 'paypal'},
        {'amount': Decimal('3000.00'), 'date': end_date - timedelta(days=15), 'status': 'paid', 'method': 'bank'},
        {'amount': Decimal('2000.00'), 'date': end_date - timedelta(days=25), 'status': 'paid', 'method': 'paypal'},
        {'amount': Decimal('1500.00'), 'date': end_date - timedelta(days=30), 'status': 'paid', 'method': 'paypal'},
        {'amount': Decimal('1200.00'), 'date': end_date, 'status': 'pending', 'method': 'paypal'},
    ]
    
    # Create payout records
    payouts_created = []
    for payout_data in payouts_data:
        payout = InstructorPayout.objects.create(
            instructor=instructor,
            amount=payout_data['amount'],
            date=payout_data['date'],
            status=payout_data['status'],
            method=payout_data['method']
        )
        payouts_created.append(payout)
    
    print(f"Created {len(payouts_created)} payout records")
    
    # Calculate totals
    total_earnings = sum(earning.amount for earning in earnings_created)
    total_payouts = sum(payout.amount for payout in payouts_created if payout.status == 'paid')
    pending_payouts = sum(payout.amount for payout in payouts_created if payout.status == 'pending')
    
    print(f"\nSummary:")
    print(f"Total Earnings: ${total_earnings}")
    print(f"Total Payouts: ${total_payouts}")
    print(f"Pending Payouts: ${pending_payouts}")
    print(f"Available Balance: ${total_earnings - total_payouts}")
    
    print("\nEarnings data inserted successfully!")
    print("You can now test the earnings analytics page.")

if __name__ == '__main__':
    insert_earnings_data() 