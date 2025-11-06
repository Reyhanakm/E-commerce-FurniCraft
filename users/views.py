from django.shortcuts import render,redirect
from django.contrib.auth import authenticate,login,logout
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


def user_register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        print("form is valid?",form.is_valid()) 
        print("form is error: ",form.errors)
        
        if form.is_valid():
            cleaned_data = form.cleaned_data
            email = cleaned_data['email']
            first_name = cleaned_data['first_name']
            last_name = cleaned_data['last_name']
            phone = cleaned_data['phone_number']
            password = cleaned_data['password']


            #  Generate OTP
            otp = str(random.randint(100000, 999999))
            # prepare user-data
            registration_data = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone_number': phone,
                'password': password,
                'otp':otp,
                'otp_created_at':timezone.now().timestamp()  #store time
                
            }


            # Save to Redis (expires in 5 minutes)
            cache.set(f"otp:{email}", json.dumps(registration_data), timeout=300)


            print(otp)
            #  Send OTP via email
            send_mail(
                subject="Your FurniCraft OTP Code",
                message=f"Your OTP code is {otp}. It expires in 5 minutes.",
                from_email="furnicraftapp@gmail.com",
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(request, "OTP sent to your email. Please verify.")
            return redirect(f"{reverse('verify_otp')}?email={email}")  # You'll handle OTP verification next

        else:
            # Django automatically displays validation errors in the form
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, 'user/register.html', {'form': form})


@never_cache
def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        # email = request.POST.get('email') #hidden input in form
        email = request.GET.get('email') or request.session.get('email')  # fallback

        if not email:
            messages.error(request, "Email missing. Please register again.")
            return redirect('user_register')

        data = cache.get(f"otp:{email}")

        if not data:
            messages.error(request, "Session expired. Please register again.")
            return redirect('user_register')

        user_data= json.loads(data)
        actual_otp=user_data.get('otp')
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

            # # Clear session data
            # del request.session['otp']
            # del request.session['registration_data']

            # clear Redis cache
            cache.delete(f"otp:{email}")

            messages.success(request, "Account created successfully! You can now log in.")
            return redirect('user_login')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect('verify_otp')
    else:
        email=request.GET.get('email')
        return render(request, 'user/verify_otp.html',{'email':email})




def resend_otp(request):
    email=request.GET.get('email')
    data=cache.get(f"otp:{email}")

    if not data:
        messages.error(request,"Session expired.Please Register again.")
        return redirect('user_register')
    
    user_data= json.loads(data)
    last_sent_time= user_data.get('otp_created_at',0)
    elapsed=timezone.now().timestamp - last_sent_time

    if elapsed < 60:  # 1 min cooldown
        messages.error(request, f"Please wait {int(60 - elapsed)} seconds before requesting a new OTP.")
        return redirect('verify_otp')

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
    return redirect('verify_otp')




def forgot_password(request):
    if request.method=='POST':
        email=request.POST.get('email')
        try:
            user=User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request,'No account found with this email.')
            return redirect('forgot_password')
        


def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request,email=email,password=password)
        if user is not None:
            login(request,user)
            return redirect('home')

        else:
            messages.error(request,"Invalid email or password.")
    return render(request,'user/login.html')


@never_cache
@login_required
def home(request):
#    if request.user.is_authenticated:
        print("user home page")
        return render(request,'user/home.html')
   

def user_logout(request):
    logout(request)
    return redirect(user_login)