from django.shortcuts import render,redirect
from django.contrib.auth import authenticate,login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User,EmailOTP
import random
from django.core.mail import send_mail
from django.utils import timezone
from .forms import RegistrationForm


def user_register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        
        if form.is_valid():
            cleaned_data = form.cleaned_data
            email = cleaned_data['email']
            first_name = cleaned_data['first_name']
            last_name = cleaned_data['last_name']
            phone = cleaned_data['phone_number']
            password = cleaned_data['password']

            #  Store registration data temporarily in session
            request.session['registration_data'] = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone_number': phone,
                'password': password,
            }

            #  Generate OTP
            otp = str(random.randint(100000, 999999))
            request.session['otp'] = otp  # store temporarily

            #  Send OTP via email
            send_mail(
                subject="Your FurniCraft OTP Code",
                message=f"Your OTP code is {otp}. It expires in 5 minutes.",
                from_email="furnicraftapp@gmail.com",
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(request, "OTP sent to your email. Please verify.")
            return redirect('verify_otp')  # You'll handle OTP verification next

        else:
            # Django automatically displays validation errors in the form
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, 'users/register.html', {'form': form})



def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        session_otp = request.session.get('otp')
        data = request.session.get('registration_data')

        if not data:
            messages.error(request, "Session expired. Please register again.")
            return redirect('user_register')

        if entered_otp == session_otp:
            # Create and activate user
            user = User.objects.create_user(
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone_number=data['phone_number'],
                password=data['password'],
                is_blocked=False
            )

            # Clear session data
            del request.session['otp']
            del request.session['registration_data']

            messages.success(request, "Account created successfully! You can now log in.")
            return redirect('user_login')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect('verify_otp')

    return render(request, 'users/verify_otp.html')




def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')# Create your views here.
        password = request.POST.get('password')
        user = authenticate(request,email=email,password=password)
        if user is not None:
            if user.is_admin:
                login(request,user)
                return redirect('admin_dashboard')
            else:
                messages.error(request,"You are not autherized to access admin panel.")
        else:
            messages.error(request,"Invalid email or password.")
    return render(request,'admin/login.html')

@login_required(login_url='admin_login')
def admin_dashboard(request):
    if not request.user.is_admin:
        messages.error(request,"Unautherized access!")
        return redirect('admin_login')
    return render(request,'admin/dashboard.html')


def admin_logout(request):
    logout(request)
    return redirect('admin_login')