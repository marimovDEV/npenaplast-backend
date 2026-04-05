import os
import sys
import django

# Setup Django environment
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from accounts.models import User

# Check if user already exists
if not User.objects.filter(username='test_admin').exists():
    User.objects.create_superuser('test_admin', 'test@example.com', 'password123')
    print("User 'test_admin' created successfully.")
else:
    # Ensure superuser permissions and update password
    user = User.objects.get(username='test_admin')
    user.set_password('password123')
    user.is_superuser = True
    user.is_staff = True
    user.save()
    print("User 'test_admin' already exists. Password updated.")
