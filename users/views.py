from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import update_session_auth_hash
from django.http import HttpResponse
from django.urls import reverse
import re
import logging

from django.db import transaction
from users.utils import generate_unique_referral_code
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from .models import User,UserAddress,Referral
from commerce.models import Wallet,WalletTransaction
import json
import random
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone
from .forms import RegistrationForm,ForgotPasswordForm, ResetOTPForm, ResetPasswordForm,LoginForm,AddressForm
from product.models import Category
from users.decorators import block_check
from admin_app.models import Banner
from utils.otp import create_and_send_otp, get_remaining_otp_cooldown,validate_otp,otp_cache_key
from django.contrib.auth import update_session_auth_hash

logger = logging.getLogger('users')

@never_cache
def user_register(request):
    logger.info("User registration started")
    if request.method == 'POST':
        logger.info("POST request received for registration")
        form = RegistrationForm(request.POST)
        print("form is valid?", form.is_valid()) 
        print("form is error: ", form.errors)
        
        if form.is_valid():
            cleaned_data = form.cleaned_data
            email = cleaned_data['email']
            referral_code = cleaned_data.get('referralcode')

            request.session['pending_email']=email
           
            referredby = None
            if referral_code:
                try:
                    referrer = User.objects.get(referralcode=referral_code)
                    referredby=referrer.id
                except User.DoesNotExist:
                    messages.warning(request,"Invalid referral code. Continuing without referral.")
        
            registration_data = {
                'email': email,
                'first_name': cleaned_data["first_name"],
                'last_name': cleaned_data["last_name"],
                'phone_number': cleaned_data["phone_number"],
                'password': cleaned_data["password"], 
                'referredby':referredby,             
            }

            # Save to Redis
            cache.set(f"user_register:{email}", json.dumps(registration_data), timeout=300)

            
            otp=create_and_send_otp(
            email=email,
            purpose="register",
            subject="Your Furnicraft Registration OTP"
            )

            print("Debug OTP: ",otp)
            
            messages.success(request, "OTP sent to your email.")
            logger.info(f"OTP email sent to {email}")
            return redirect('verify_otp')

        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, 'user/register.html', {'form': form})


@block_check
@never_cache
def verify_otp(request):
    email = request.session.get('pending_email')
    if not email:
            messages.error(request, "Email missing. Please register again.")
            return redirect('user_register')
    remaining_seconds = get_remaining_otp_cooldown(email, "register")

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')

        valid,msg = validate_otp(email,"register",entered_otp)

        if not valid:
            messages.error(request,msg)
            return redirect("verify_otp")

        data = cache.get(f"user_register:{email}")

        if not data:
            messages.error(request, "Session expired. Please register again.")
            return redirect('user_register')

        reg = json.loads(data)
        print("Entered OTP:", entered_otp)

        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                first_name=reg['first_name'],
                last_name=reg['last_name'],
                phone_number=reg['phone_number'],
                password=reg['password'],
                referralcode=generate_unique_referral_code(),
                is_blocked=False
            )

            Wallet.objects.get_or_create(user=user)

            referrer_id=reg.get('referredby')
            if referrer_id:
                try:
                    referrer=User.objects.get(id=referrer_id)
                    if referrer!=user:
                        user.referredby=referrer
                        user.save(update_fields=["referredby"])

                        Referral.objects.get_or_create(
                            referrer=referrer,
                            referred_user=user,
                            defaults={'reward_amount':100}
                        )
                        
                except User.DoesNotExist:
                    pass
                
        # Clear Redis cache
        cache.delete(f"user_register:{email}")
        cache.delete(otp_cache_key("register", email))
        del request.session['pending_email']

        messages.success(request, "Account created successfully! You can now log in.")
        return redirect('user_login')
    
    return render(request, 'user/verify_otp.html',{
    "remaining_seconds": remaining_seconds
    })


@block_check
@never_cache
def resend_register_otp(request):
    email = request.session.get("pending_email")

    if not email:
        messages.error(request, "Session expired. Please register again.")
        return redirect("user_register")

    key = otp_cache_key("register", email)
    data = cache.get(key)


    if not data:
        messages.error(request, "OTP expired. Please register again.")
        return redirect("user_register")

    otp_data = json.loads(data)
    last_sent = otp_data.get("otp_created_at", 0)
    elapsed = timezone.now().timestamp() - last_sent

    # COOLDOWN LIMIT
    if elapsed < 60:
        messages.error(request, f"Please wait {int(60 - elapsed)} seconds before resending OTP.")
        return redirect("verify_otp")

    new_otp = create_and_send_otp(
        email=email,
        purpose="register",
        subject="Your new FurniCraft Registration OTP"
    )

    print("RESEND REGISTER OTP:", new_otp)

    messages.success(request, "A new OTP has been sent.")
    return redirect("verify_otp")



@never_cache
def forgot_password(request):
    form = ForgotPasswordForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        request.session['pending_email'] = email

        if not User.objects.filter(email=email).exists():
            messages.error(request, "No account found with this email.")
            return redirect("forgot_password")

        otp = create_and_send_otp(
            email=email,
            purpose="reset_password",
            subject="Your FurniCraft Password Reset OTP"
        )
        print("reset password OTP:", otp)

        messages.success(request, "OTP sent to your email.")
        return redirect('reset_password_verify')

    return render(request, 'user/profile/forgot_password.html', {'form': form})



@block_check
@never_cache
def reset_password_verify(request):
    email = request.session.get('pending_email')
    if not email:
        messages.error(request, "Session expired. Please try again.")
        return redirect('forgot_password')
    remaining_seconds = get_remaining_otp_cooldown(email,"reset_password")
    
    otp_verified = request.session.get("reset_otp_verified", False)
    otp_form = ResetOTPForm()
    password_form = ResetPasswordForm()
    
    if request.method == 'POST' and not otp_verified and 'otp' in request.POST:
        otp_form = ResetOTPForm(request.POST)
        if otp_form.is_valid():
            otp = otp_form.cleaned_data['otp']

            if not otp:
                messages.error(request, "Please enter the OTP.")
                return redirect("reset_password_verify")

            valid, msg = validate_otp(email, "reset_password", otp)
            if not valid:
                messages.error(request, msg)
                return redirect("reset_password_verify")
            
            request.session['reset_otp_verified'] = True
            messages.success(request, "OTP verified. Please set a new password.")
            return redirect("reset_password_verify")

    if request.method == 'POST' and otp_verified:
        password_form = ResetPasswordForm(request.POST)

        if password_form.is_valid():
           
            user = get_object_or_404(User, email=email)
            user.set_password(password_form.cleaned_data['new_password'])
            user.save()

            # invalidate sessions properly
            update_session_auth_hash(request, user)

            request.session.pop('pending_email', None)
            request.session.pop('reset_otp_verified', None)

            messages.success(request, "Password reset successful!")
            return redirect('user_login')
    print(password_form.errors)
    return render(request, 'user/reset_password_verify.html', {'password_form': password_form,
                                                               'otp_form':otp_form, 
                                                               'email': email,
                                                               "otp_verified": otp_verified,
                                                               'remaining_seconds': remaining_seconds,})


@never_cache
def resend_reset_password_otp(request):
    email = request.session.get("pending_email")

    if not email:
        return redirect("forgot_password")

    key = otp_cache_key("reset_password", email)
    data = cache.get(key)

    if not data:
        messages.error(request, "OTP expired. Please try again.")
        return redirect("forgot_password")

    otp_data = json.loads(data)
    elapsed = timezone.now().timestamp() - otp_data["otp_created_at"]

    if elapsed < 60:
        messages.error(request, f"Wait {int(60 - elapsed)} seconds before resending OTP.")
        return redirect("reset_password_verify")

    otp = create_and_send_otp(
        email=email,
        purpose="reset_password",
        subject="Your new FurniCraft Password Reset OTP"
    )
    print("RESEND RESET PASSWORD OTP:", otp)

    messages.success(request, "A new OTP has been sent.")
    return redirect("reset_password_verify")


@never_cache
def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = LoginForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user = authenticate(request, email=email, password=password)

            if user:
                if user.is_blocked:
                    messages.error(request, "Your account has been blocked. Please contact support.")
                    return render(request, 'user/login.html', {'form': form})
                
                login(request, user)
                messages.success(request, f"Welcome, {user.first_name}!")
                return redirect('home')


            form.add_error(None, "Invalid email or password.")

    return render(request, 'user/login.html', {'form': form})


@block_check
@never_cache
@login_required(login_url="/login")
def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('user_login')


@block_check
@login_required
def home(request):
    banners=Banner.objects.filter(status=True).order_by('id')
    categories=Category.objects.all()
    return render(request,'user/home.html',{'categories':categories,'banners':banners})


def landing(request):
    banners=Banner.objects.filter(status=True).order_by('id')   
    categories=Category.objects.all()
    return render(request,'user/landing.html',{'categories':categories,'banners':banners})

@login_required
@never_cache
def change_email_request_old_otp(request):
    if request.session.get("email_change_old_verified"):
        return redirect("change_email_enter_new")

    old_email = request.user.email

    otp = create_and_send_otp(
        email=old_email,
        purpose="email_change_old",
        subject="Verify Your Current Email"
    )

    print("OLD EMAIL OTP:", otp)

    request.session["email_change_old_pending"] = True
    messages.info(request, f"OTP sent to your current email: {old_email}")
    return redirect("change_email_verify_old")

@login_required
@never_cache
def change_email_verify_old(request):
    if not request.session.get("email_change_old_pending"):
        return redirect("change_email_request_old_otp")

    old_email = request.user.email

    if request.method == "POST":
        otp = request.POST.get("otp")

        valid, msg = validate_otp(old_email, "email_change_old", otp)

        if not valid:
            messages.error(request, msg)
            return render(request, "user/profile/change_email_verify_old.html", {'old_email': old_email}) 
        request.session["email_change_old_verified"] = True
        request.session.pop("email_change_old_pending", None)
        messages.success(request, "Current email verified. Now enter your new email.")
        return redirect("change_email_enter_new")

    return render(request, "user/profile/change_email_verify_old.html", {'old_email': old_email})


@login_required
@never_cache
def change_email_enter_new(request):
    if not request.session.get("email_change_old_verified"):
        return redirect("change_email_request_old_otp")
    
    if request.method == "POST":
        new_email = request.POST.get("new_email")

        if User.objects.filter(email=new_email).exists():
            messages.error(request, "Email already in use.")
            return render(request, "user/profile/change_email_enter_new.html") 
        
        request.session["pending_new_email"] = new_email
        return redirect("change_email_request_new_otp")

    return render(request, "user/profile/change_email_enter_new.html")


@login_required
@never_cache
def change_email_request_new_otp(request):
    if not request.session.get("email_change_old_verified"):
        return redirect("change_email_request_old_otp")

    new_email = request.session.get("pending_new_email")

    if not new_email:
            return redirect("change_email_enter_new")
    
    otp = create_and_send_otp(
        email=new_email,
        purpose="email_change_new",
        subject="Verify Your New Email"
    )

    print("NEW EMAIL OTP:", otp)

    messages.info(request, f"OTP sent to your new email: {new_email}")
    return redirect("change_email_verify_new")

@login_required
@never_cache
def change_email_verify_new(request):
    new_email = request.session.get("pending_new_email")

    if not new_email:
        return redirect("change_email_enter_new")

    if request.method == "POST":
        otp = request.POST.get("otp")

        valid, msg = validate_otp(new_email, "email_change_new", otp)

        if not valid:
            messages.error(request, msg)
            return render(request, "user/profile/change_email_verify_new.html", {'new_email': new_email})
        
        user = request.user
        user.email = new_email
        user.save()

        for key in ["pending_new_email", "email_change_old_verified"]:
            request.session.pop(key, None)

        messages.success(request, "Email updated successfully!")
        redirect_url = reverse("edit_profile") 
  
        response = HttpResponse(status=204) 
        response["HX-Redirect"] = redirect_url
        
        return response


    return render(request, "user/profile/change_email_verify_new.html", {'new_email': new_email})

@login_required
@never_cache
def resend_email_change_old_otp(request):
    old_email = request.user.email

    key = otp_cache_key("email_change_old", old_email)
    data = cache.get(key)

    if not data:
        messages.error(request, "OTP expired. Start again.")
        return redirect("change_email_enter_new")

    otp_data = json.loads(data)
    elapsed = timezone.now().timestamp() - otp_data["otp_created_at"]

    if elapsed < 60:
        messages.error(request, f"Wait {int(60 - elapsed)} seconds to resend OTP.")
        return redirect("change_email_verify_old")

    otp = create_and_send_otp(
        email=old_email,
        purpose="email_change_old",
        subject="Your FurniCraft Email Change OTP"
    )

    print("RESEND OLD EMAIL OTP:", otp)

    messages.success(request, "New OTP sent to your current email.")
    return redirect("change_email_verify_old")

@login_required
@never_cache
def resend_email_change_new_otp(request):
    new_email = request.session.get("pending_new_email")

    if not new_email:
        messages.error(request, "Session expired. Start again.")
        return redirect("change_email_request_old_otp")

    key = otp_cache_key("email_change_new", new_email)
    data = cache.get(key)

    if not data:
        messages.error(request, "OTP expired. Start again.")
        return redirect("change_email_enter_new")

    otp_data = json.loads(data)
    elapsed = timezone.now().timestamp() - otp_data["otp_created_at"]

    if elapsed < 60:
        messages.error(request, f"Wait {int(60 - elapsed)} seconds to resend OTP.")
        return redirect("change_email_verify_new")

    otp = create_and_send_otp(
        email=new_email,
        purpose="email_change_new",
        subject="Your new FurniCraft Email Verification OTP"
    )

    print("RESEND NEW EMAIL OTP:", otp)

    messages.success(request, "New OTP sent to your new email.")
    return redirect("change_email_verify_new")

@login_required
@never_cache
def change_password_verify_current(request):
    if request.method == "GET":
        return render(request, "user/profile/change_password_verify_current.html")

    current_password = request.POST.get("current_password")

    if not request.user.check_password(current_password):
        messages.error(request, "Incorrect current password")
        return render(request, "user/profile/change_password_verify_current.html")

    
    request.session["password_verified"] = True

    return render(request, "user/profile/change_password_new.html")

@login_required
@never_cache
def change_password_set_new(request):
    if not request.session.get("password_verified"):
        return render(request, "user/profile/change_password_verify_current.html")

    new = request.POST.get("new_password")
    confirm = request.POST.get("confirm_password")

    if new != confirm:
        messages.error(request, "Passwords do not match")
        return render(request, "user/profile/change_password_new.html")
    user=request.user
    user.set_password(new)
    user.save()

    update_session_auth_hash(request, user)
    request.session.pop("password_verified", None)

    messages.success(request, "Password changed successfully!")
    return render(request, "user/profile/change_password_success.html")


@login_required
def edit_address(request, pk):
    address = get_object_or_404(UserAddress, id=pk, user=request.user)

    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)

        if form.is_valid():
            form.save() 

            if request.headers.get("HX-Request"):
                return render(request, "user/profile/_address_list_partial.html", {
                    "addresses": request.user.addresses.filter(is_deleted=False)
                })

            return redirect('my_address')

        if request.headers.get("HX-Request"):
            return render(request, "user/profile/_edit_address_partial.html", {
                "form": form, "address": address
            })

    form = AddressForm(instance=address)

    return render(request, "user/profile/_edit_address_partial.html", {
        "form": form, "address": address
    })


@login_required
def delete_address(request, pk):
    source = request.GET.get("from", "profile")

    address = get_object_or_404(UserAddress, id=pk, user=request.user)
    address.is_deleted = True
    address.save()

    addresses = request.user.addresses.filter(is_deleted=False).order_by('-created_at')

    if source == "checkout":
        default_address = addresses.filter(is_default=True).first()

        return render(
            request,
            "commerce/checkout/_address_list_partial.html",
            {
                "addresses": addresses,
                "selected_address": default_address.id if default_address else None
            }
        )

    messages.success(request, "Address deleted successfully!")
    return render(
        request,
        "user/profile/_address_list_partial.html",
        {"addresses": addresses}
    )

@block_check
@login_required
def my_address(request):
    return render(request, "user/profile/_address_list_partial.html", {
        "addresses": request.user.addresses.filter(is_deleted=False).order_by('-created_at'),
        "user": request.user
    })


@login_required
def set_default_address(request, pk):
    address = get_object_or_404(UserAddress, id=pk, user=request.user)
    address.is_default = True
    address.save() 

    return render(request, "user/profile/_address_list_partial.html", {
        "addresses": request.user.addresses.filter(is_deleted=False).order_by('-created_at'),
        "user": request.user
    })

@login_required
def add_address(request):
    source = request.GET.get("from", "profile")

    if request.method == 'POST':
        form = AddressForm(request.POST,initial={'user':request.user})

        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()

            if request.headers.get("HX-Request"):
                if source == "checkout":
                    return render(
                        request,
                        "commerce/checkout/_address_list_partial.html",
                        {
                            "addresses": request.user.addresses.filter(is_deleted=False).order_by('-created_at'),
                            "selected_address": address.id,
                            "has_address":True
                        }
                    )

                return render(
                    request,
                    "user/profile/_address_list_partial.html",
                    {
                        "addresses": request.user.addresses.filter(is_deleted=False).order_by('-created_at')
                    }
                )

            return redirect("my_address")

        if request.headers.get("HX-Request"):
            return render(
                request,
                "user/profile/_add_address_partial.html",
                {"form": form}
            )

    form = AddressForm(initial={'user':request.user})
    return render(
        request,
        "user/profile/_add_address_partial.html",
        {"form": form}
    )


@block_check
@login_required
def my_profile(request):
    user=request.user
    if not user.referralcode:
        with transaction.atomic():
            # re-check inside transaction
            user.refresh_from_db()
            if not user.referralcode:
                user.referralcode=generate_unique_referral_code()
                user.save(update_fields=["referralcode"])
    if request.headers.get("HX-Request"):
        return render(request,"user/profile/_profile_partial.html",{"user":user})
    return render(request,'user/profile/my_profile.html',{'user':user})


@login_required
def edit_profile(request):
    user = request.user
    
    if request.method == 'POST':
        
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.phone_number = request.POST.get('phone_number', user.phone_number) 
        
        
        if 'image' in request.FILES:
            user.image = request.FILES['image']
            
        user.save()
        
        return render(request, "user/profile/_profile_partial.html", {'user': user})

    return render(request, "user/profile/_edit_profile_form.html", {'user': user})
            


