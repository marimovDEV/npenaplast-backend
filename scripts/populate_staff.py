import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import ERPRole, Department

User = get_user_model()

def populate():
    # 1. Create Departments
    departments = [
        'Ma\'muriyat', 'Sotuv', 'Ishlab chiqarish', 'Logistika', 'Ombor', 'Sifat Nazorati'
    ]
    dept_objs = {}
    for d in departments:
        obj, _ = Department.objects.get_or_create(name=d)
        dept_objs[d] = obj
    
    # 2. Define Roles
    roles_names = [
        'Bosh Admin', 'Sotuv menejeri', 'Ishlab chiqarish ustasi', 
        'CNC operatori', 'Pardozlovchi', 'Chiqindi operatori', 
        'Sifat nazoratchisi', 'Kuryer', 'Omborchi'
    ]
    
    role_objs = {}
    for r_name in roles_names:
        obj, _ = ERPRole.objects.get_or_create(name=r_name)
        role_objs[r_name] = obj
        
    # 3. Create Users
    users_to_create = [
        ('admin', 'Alisher Odilov', 'Bosh Admin', 'Ma\'muriyat', '998901234567'),
        ('sales_jamshid', 'Jamshid Karimov', 'Sotuv menejeri', 'Sotuv', '998901234568'),
        ('usta_dilshod', 'Dilshod Rahimov', 'Ishlab chiqarish ustasi', 'Ishlab chiqarish', '998901234569'),
        ('cnc_ali', 'Ali Valiyev', 'CNC operatori', 'Ishlab chiqarish', '998901234570'),
        ('finisher_bobur', 'Bobur Mirzo', 'Pardozlovchi', 'Ishlab chiqarish', '998901234571'),
        ('waste_hasan', 'Hasan Akramov', 'Chiqindi operatori', 'Ishlab chiqarish', '998901234572'),
        ('qc_nodir', 'Nodir Sodiqov', 'Sifat nazoratchisi', 'Sifat Nazorati', '998901234573'),
        ('kuryer_rustam', 'Rustam Ganiyev', 'Kuryer', 'Logistika', '998901234574'),
        ('ombor_olim', 'Olim Jo\'rayev', 'Omborchi', 'Ombor', '998901234575')
    ]
    
    password = 'penoplast2026'
    
    for uname, fname, rname, dname, phone in users_to_create:
        user, created = User.objects.get_or_create(username=uname)
        user.full_name = fname
        user.first_name = fname.split(' ')[0]
        user.last_name = fname.split(' ')[-1]
        user.phone = phone
        user.set_password(password)
        
        user.role_obj = role_objs[rname]
        user.department = dept_objs[dname]
        user.role = rname # Legacy field
        
        user.is_staff = (rname in ['Bosh Admin', 'Admin'])
        user.is_superuser = (rname == 'Bosh Admin')
        
        user.save()
        status = "Created" if created else "Updated"
        print(f"[{status}] {uname} ({rname}) - {phone}")

populate()
