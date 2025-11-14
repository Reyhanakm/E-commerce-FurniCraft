from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.cache import never_cache
from .models import User
import random
from django.core.cache import cache
import json
from django.core.mail import send_mail
from django.utils import timezone
from .forms import RegistrationForm
from admin_app.models import Category,Product,ProductImage


def user_register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        print("form is valid?", form.is_valid()) 
        print("form is error: ", form.errors)
        
        if form.is_valid():
            cleaned_data = form.cleaned_data
            email = cleaned_data['email']
            first_name = cleaned_data['first_name']
            last_name = cleaned_data['last_name']
            phone = cleaned_data['phone_number']
            password = cleaned_data['password']

            # Generate OTP
            otp = str(random.randint(100000, 999999))
            
            # Prepare user-data
            registration_data = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone_number': phone,
                'password': password,
                'otp': otp,
                'otp_created_at': timezone.now().timestamp()
            }

            # Save to Redis (expires in 5 minutes)
            cache.set(f"otp:{email}", json.dumps(registration_data), timeout=300)

            print(otp)
            
            # Send OTP via email
            send_mail(
                subject="Your FurniCraft OTP Code",
                message=f"Your OTP code is {otp}. It expires in 5 minutes.",
                from_email="furnicraftapp@gmail.com",
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(request, "OTP sent to your email. Please verify.")
            return redirect(f"{reverse('verify_otp')}?email={email}")

        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, 'user/register.html', {'form': form})


@never_cache
def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        email = request.GET.get('email') or request.session.get('email')

        if not email:
            messages.error(request, "Email missing. Please register again.")
            return redirect('user_register')

        data = cache.get(f"otp:{email}")

        if not data:
            messages.error(request, "Session expired. Please register again.")
            return redirect('user_register')

        user_data = json.loads(data)
        actual_otp = user_data.get('otp')
        print("Entered OTP:", entered_otp)
        print("Actual OTP:", actual_otp)

        if entered_otp == actual_otp:
            # Create and activate user
            user = User.objects.create_user(
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                phone_number=user_data['phone_number'],
                password=user_data['password'],
                referralcode=user_data.get('referralcode'),
                is_blocked=False
            )

            # Clear Redis cache
            cache.delete(f"otp:{email}")

            messages.success(request, "Account created successfully! You can now log in.")
            return redirect('user_login')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect(f"{reverse('verify_otp')}?email={email}")
    else:
        email = request.GET.get('email')
        return render(request, 'user/verify_otp.html', {'email': email})


def resend_otp(request):
    email = request.GET.get('email')
    data = cache.get(f"otp:{email}")

    if not data:
        messages.error(request, "Session expired. Please register again.")
        return redirect('user_register')
    
    user_data = json.loads(data)
    last_sent_time = user_data.get('otp_created_at', 0)
    elapsed = timezone.now().timestamp() - last_sent_time

    if elapsed < 60:  # 1 min cooldown
        messages.error(request, f"Please wait {int(60 - elapsed)} seconds before requesting a new OTP.")
        return redirect(f"{reverse('verify_otp')}?email={email}")

    # Generate and update OTP
    new_otp = str(random.randint(100000, 999999))
    user_data['otp'] = new_otp
    user_data['otp_created_at'] = timezone.now().timestamp()

    # Update Redis
    cache.set(f"otp:{email}", json.dumps(user_data), timeout=300)

    # Send OTP again
    send_mail(
        subject="Your new FurniCraft OTP Code",
        message=f"Your new OTP is {new_otp}. It expires in 5 minutes.",
        from_email="furnicraftapp@gmail.com",
        recipient_list=[email],
        fail_silently=False,
    )

    print("New OTP:", new_otp)
    messages.success(request, "A new OTP has been sent to your email.")
    return redirect(f"{reverse('verify_otp')}?email={email}")


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email)
            
            # Generate OTP for password reset
            otp = str(random.randint(100000, 999999))
            
            # Store reset data in cache
            reset_data = {
                'email': email,
                'otp': otp,
                'otp_created_at': timezone.now().timestamp()
            }
            
            cache.set(f"password_reset:{email}", json.dumps(reset_data), timeout=300)
            
            # Send OTP via email
            send_mail(
                subject="FurniCraft Password Reset OTP",
                message=f"Your password reset OTP is {otp}. It expires in 5 minutes.",
                from_email="reyhanakm112@gmail.com",
                recipient_list=[email],
                fail_silently=False,
            )
            
            print("Password Reset OTP:", otp)
            messages.success(request, "OTP sent to your email. Please check your inbox.")
            return redirect(f"{reverse('reset_password_verify')}?email={email}")
            
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email.')
            return redirect('forgot_password')
    
    return render(request, 'user/forgot_password.html')


@never_cache
def reset_password_verify(request):
    if request.method == 'POST':
        email = request.GET.get('email')
        entered_otp = request.POST.get('otp')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not email:
            messages.error(request, "Email missing. Please try again.")
            return redirect('forgot_password')
        
        data = cache.get(f"password_reset:{email}")
        
        if not data:
            messages.error(request, "Session expired. Please request a new OTP.")
            return redirect('forgot_password')
        
        reset_data = json.loads(data)
        actual_otp = reset_data.get('otp')
        
        if entered_otp != actual_otp:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect(f"{reverse('reset_password_verify')}?email={email}")
        
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect(f"{reverse('reset_password_verify')}?email={email}")
        
        # Update password
        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            
            # Clear cache
            cache.delete(f"password_reset:{email}")
            
            messages.success(request, "Password reset successful! Please log in with your new password.")
            return redirect('user_login')
            
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('forgot_password')
    
    else:
        email = request.GET.get('email')
        return render(request, 'user/reset_password_verify.html', {'email': email})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            if user.is_blocked:
                messages.error(request, "Your account has been blocked. Please contact support.")
                return render(request, 'user/login.html')
            
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name}!")
            return redirect('home')
        else:
            messages.error(request, "Invalid email or password.")
    
    return render(request, 'user/login.html')


# @never_cache
# @login_required
# def home(request):
#     print("User home page")
#     return render(request, 'user/home.html')


def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('user_login')


@login_required
def home(request):
    categories=Category.objects.all()
    return render(request,'user/home.html',{'categories':categories})

@login_required
def category_products(request,id):
    category=get_object_or_404(id=id,is_deleted=False)
    products=Product.objects.filter(category=category,is_deleted=False)

    product_images=ProductImage.objects.filter(product__in=products).order_by('-is_primary','id')

    for img in
    
