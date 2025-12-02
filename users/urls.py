from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
  
    path('home/', views.home, name='home'),
 
    path('register/', views.user_register, name='user_register'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_register_otp, name='resend_otp'),

    
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password-verify/', views.reset_password_verify, name='reset_password_verify'),
    path('resend-reset-password-otp/', views.resend_reset_password_otp, name='resend_reset_password_otp'),
    

    # path('profile/',views.my_profile,name='my_profile'),
    # path('profile/edit/',views.edit_profile,name='edit_profile'),
    # path('profile/edit/password/', views.change_password, name='change_password'),
    # path('profile/address/', views.my_address, name='my_address'), 
    # path('profile/orders/', views.my_orders, name='my_orders'),   
    
    
    path('change-email/request-old-otp/',views.change_email_request_old_otp,name='change_email_request_old_otp'),
    path('change-email/verify-old/',views.change_email_verify_old,name='change_email_verify_old'),
    path('change-email/enter-new/',views.change_email_enter_new,name='change_email_enter_new'),
    path('change-email/request-new-otp/',views.change_email_request_new_otp,name='change_email_request_new_otp'),
    path('change-email/verify-new/',views.change_email_verify_new,name='change_email_verify_new'),

    
    path('change-email/resend/old/',views.resend_email_change_old_otp, name='resend_email_change_old_otp'),
    path('change-email/resend/new/',views.resend_email_change_new_otp,name='resend_email_change_new_otp'),
    
]