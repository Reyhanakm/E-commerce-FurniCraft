from django.urls import path
from . import views

urlpatterns = [
    path('admin/',views.admin_login,name='admin_login'),
    path('admin/dashboard/',views.admin_dashboard,name='admin_dashboard'),
    path('admin/logout/',views.admin_logout,name='admin_logout'),
    path('register/',views.user_register,name='user_register'),
    path('verify_otp/',views.verify_otp,name='verify_otp')

]