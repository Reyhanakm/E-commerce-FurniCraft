from django.urls import path
from . import views

urlpatterns = [
    path('login/',views.user_login,name='user_login'),
    path('home/',views.home,name='home'),
    path('logout/',views.user_logout,name='user_logout'),
    path('register/',views.user_register,name='user_register'),
    path('verify_otp/',views.verify_otp,name='verify_otp'),
    path('resend_otp/',views.resend_otp,name='resend_otp'),

]