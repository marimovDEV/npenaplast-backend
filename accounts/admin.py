from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'role', 'is_active')
    search_fields = ('username', 'full_name', 'phone')
    list_filter = ('role', 'is_active')
