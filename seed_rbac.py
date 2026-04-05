import os
import sys
import django

# Ensure project root is in path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')
django.setup()

from accounts.models import User, ERPRole, ERPPermission

def seed_rbac():
    # Define Permissions
    perms_data = [
        ('warehouse.view', "Omborni ko'rish"),
        ('warehouse.create', "Yangi mahsulot/kirim yaratish"),
        ('warehouse.move', "Mahsulot ko'chirish (transfer)"),
        ('warehouse.delete', "Ombor ma'lumotlarini o'chirish"),
        # Production
        ('production.start', "Ishlab chiqarishni boshlash"),
        ('production.stop', "Ishlab chiqarishni yakunlash"),
        ('production.writeoff', "Brak/Chiqindi hisobga olish"),
        # Finance
        ('finance.view', "Moliya/Sotuvni ko'rish"),
        ('finance.edit', "Sotuv/Narxlarni o'zgartirish"),
        ('finance.delete', "Moliyaviy amallarni o'chirish"),
        # Reports
        ('reports.view', "Hisobotlarni ko'rish"),
        ('reports.export', "Hisobotlarni eksport qilish (Excel/PDF)"),
    ]

    perms = {}
    for key, name in perms_data:
        p, _ = ERPPermission.objects.get_or_create(key=key, defaults={'name': name})
        perms[key] = p

    # Define Roles
    roles_data = {
        'Bosh Admin': list(perms.keys()),
        'Admin': list(perms.keys()),
        'Omborchi': ['warehouse.view', 'warehouse.move'],
        'Ishlab chiqarish ustasi': ['production.start', 'production.stop', 'warehouse.view'],
        'CNC operatori': ['production.start', 'production.stop'],
        'Pardozlovchi': ['production.start', 'production.stop'],
        'Chiqindi operatori': ['production.writeoff'],
        'Sotuv menejeri': ['finance.view', 'reports.view'],
    }

    for role_name, p_keys in roles_data.items():
        role, _ = ERPRole.objects.get_or_create(name=role_name)
        role.permissions.set([perms[k] for k in p_keys])
        role.save()

    # Link existing users to roles
    for user in User.objects.all():
        if user.role:
            role_obj = ERPRole.objects.filter(name=user.role).first()
            if role_obj:
                user.role_obj = role_obj
                user.save()

if __name__ == "__main__":
    seed_rbac()
    print("RBAC Seeded successfully!")
