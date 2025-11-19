from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from .models import User
from django.db.models import Prefetch,Q 
import random
from django.core.paginator import Paginator
from django.core.cache import cache
import json
from django.core.mail import send_mail
from django.utils import timezone
from .forms import RegistrationForm,ForgotPasswordForm,ResetPasswordVerifyForm,LoginForm
from admin_app.models import Category,Product,ProductImage,ProductVariant


def user_register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        print("form is valid?", form.is_valid()) 
        print("form is error: ", form.errors)
        
        if form.is_valid():
            cleaned_data = form.cleaned_data
            email = cleaned_data['email']
            request.session['pending_email']=email
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
            return redirect('verify_otp')

        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, 'user/register.html', {'form': form})


@never_cache
def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        email = request.session.get('pending_email')

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
            del request.session['pending_email']
            return redirect('user_login')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect('verify_otp')
    else:
        email = request.GET.get('email')
        return render(request, 'user/verify_otp.html', {'email': email})


def resend_otp(request):
    email = request.session.get('pending_email')
    data = cache.get(f"otp:{email}")

    if not data:
        messages.error(request, "Session expired. Please try again.")
        return redirect('user_register')
    
    user_data = json.loads(data)
    last_sent_time = user_data.get('otp_created_at', 0)
    elapsed = timezone.now().timestamp() - last_sent_time

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
    form = ForgotPasswordForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data['email']
            request.session['pending_email'] = email

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, "No account found with this email.")
                return redirect('forgot_password')

            otp = str(random.randint(100000, 999999))

            reset_data = {
                'email': email,
                'otp': otp,
                'otp_created_at': timezone.now().timestamp()
            }
            cache.set(f"password_reset:{email}", json.dumps(reset_data), timeout=300)

            send_mail(
                subject="FurniCraft Password Reset OTP",
                message=f"Your OTP is {otp}. It expires in 5 minutes.",
                from_email="your-email@gmail.com",
                recipient_list=[email],
            )
            print("Resend password_otp :",otp)
            messages.success(request, "OTP sent to your email.")
            return redirect('reset_password_verify')

    return render(request, 'user/forgot_password.html', {'form': form})


@never_cache
def reset_password_verify(request):
    email = request.session.get('pending_email')
    form = ResetPasswordVerifyForm(request.POST or None)

    if not email:
        messages.error(request, "Session expired. Please try again.")
        return redirect('forgot_password')

    if request.method == 'POST':
        if form.is_valid():
            otp = form.cleaned_data['otp']
            new_password = form.cleaned_data['new_password']
            confirm_password = form.cleaned_data['confirm_new_password']

            data = cache.get(f"password_reset:{email}")

            if not data:
                messages.error(request, "OTP expired. Please request again.")
                return redirect('forgot_password')

            reset_data = json.loads(data)

            if reset_data['otp'] != otp:
                messages.error(request, "Invalid OTP.")
                return redirect('reset_password_verify')

            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return redirect('reset_password_verify')

            # Save new password
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()

            cache.delete(f"password_reset:{email}")
            del request.session['pending_email']

            messages.success(request, "Password reset successful!")
            return redirect('user_login')

    return render(request, 'user/reset_password_verify.html', {'form': form, 'email': email})


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
                messages.success(request, f"Welcome back, {user.first_name}!")
                return redirect('home')

            # Invalid login
            form.add_error(None, "Invalid email or password.")

    return render(request, 'user/login.html', {'form': form})


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
    category=get_object_or_404(Category,id=id,is_deleted=False)
    products=Product.objects.filter(category=category).prefetch_related(
        Prefetch('variants',queryset=ProductVariant.objects.order_by('id')))
    product_images=ProductImage.objects.filter(product__in=products,is_primary=True)

    image_map={img.product_id:img for img in product_images}

    for product in products:
        product.primary_image=image_map.get(product.id)
    
    return render(request,'user/category_products.html',{'products':products})

@login_required
def list_products(request):
    user=request.User.authenticate()
    if user is None:
        return redirect('user_login')
    
    products=Product.objects.all()
    return render(request,'user/list_products.html',{'products':products})



def products(request):
    products = Product.objects.prefetch_related('images', 'variants')

    # Search
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    # Category
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    # Price filter
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min:
        products = products.filter(variants__sales_price__gte=price_min)
    if price_max:
        products = products.filter(variants__sales_price__lte=price_max)
    

    # Sort
    sort = request.GET.get('sort')
    if sort == 'low_to_high':
        products = products.order_by('variants__sales_price')
    elif sort == 'high_to_low':
        products = products.order_by('-variants__sales_price')
    elif sort == 'a_to_z':
        products = products.order_by('name')
    elif sort == 'z_to_a':
        products = products.order_by('-name')
    elif sort == 'new':
        products = products.order_by('-created_at')

    # Pagination
    paginator = Paginator(products, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    params = request.GET.copy()
    if "page" in params:
        params.pop("page")
    querystring = params.urlencode()

    context = {
        "page_obj": page_obj,
        "products": page_obj.object_list,
        "categories": Category.objects.filter(is_deleted=False),
        "search": search_query,
        "querystring": querystring,
    }


    if request.headers.get("HX-Request"):
        return render(request, "user/components/product_list_partial.html", context)


    return render(request, "user/products.html", context)

def product_details(request,id):
    product=Product.objects.filter(id=id).prefetch_related('images')
    variants=product.prefetch_related('variants')
    return render(request,'user/product_details.html',{
        'product':product,
        'variants':variants,
    })

