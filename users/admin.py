from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User,UserAddress

class UserAdmin(BaseUserAdmin):
    list_display=('email','first_name','last_name','is_admin','is_blocked','created_at')
    list_filter = ('is_admin','is_blocked')
    search_fields = ('email','first_name','last_name')
    ordering = ('-created_at',)

    fieldsets = (
        (None,{'fields':('email','password')}),
        ('Personal info',{ 'fields':('first_name','last_name','phone_number','refferralcode','refferdby')}),
        ('Permissions',{'fields':('is_admin','is_blocked','is_staff','is_superuser')}),
    )

admin.site.register(User)
admin.site.register(UserAddress)