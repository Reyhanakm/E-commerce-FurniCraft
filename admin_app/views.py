import json
from django.shortcuts import render,redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login,logout
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q,Prefetch
from cloudinary.utils import cloudinary_url
from .forms import BannerForm
from .models import Banner
from commerce.models import Orders,OrderItem
from users.models import User,UserManager
from product.models import Category,Product,ProductVariant,ProductImage
from product.forms import CategoryForm,ProductForm,ProductVariantForm


def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
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
    return render(request,'admin/admin_login.html')


@never_cache
@login_required(login_url='admin_login')
def admin_dashboard(request):
    if not request.user.is_admin:
        messages.error(request,"Unautherized access!")
        return redirect('admin_login')
    return render(request,'admin/dashboard.html')


@login_required(login_url='admin_login')
def admin_logout(request):
    logout(request)
    return redirect('admin_login')


@login_required(login_url='admin_login')
def banner_page(request):
    if request.method == 'POST':
        form = BannerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("banner_page")
    else:
        form = BannerForm()

    banners = Banner.objects.all().order_by('created_at')

    return render(request, "admin/banner_page.html", {
        'add_form': form,      
        'banners': banners,    
        'edit_form': None,     
        'edit_id': None,
    })


@login_required(login_url='admin_login')
def edit_banner(request, id):
    banner = Banner.objects.get(id=id)

    if request.method == "POST":
        form = BannerForm(request.POST, request.FILES, instance=banner)
        if form.is_valid():
            form.save()
            return redirect("banner_page")
    else:
        form = BannerForm(instance=banner)

    banners = Banner.objects.all().order_by('-created_at')

    return render(request, "admin/banner_page.html", {
        'add_form': BannerForm(),   
        'edit_form': form,          
        'banners': banners,
        'edit_id': id,              
    })

@login_required(login_url='admin_login')
def delete_banner(request, id):
    banner = Banner.objects.get(id=id)
    banner.delete()   # Cloudinary image also gets removed
    return redirect("banner_page")


@login_required(login_url='admin_login')
def customer_list(request):
    search_query = request.GET.get('q', '')
    filter_status = request.GET.get('filter', '')

    customers = User.objects.all().order_by('-created_at')

    if search_query:
        customers = customers.filter(Q(first_name__icontains=search_query)|Q(last_name__icontains=search_query))

    if filter_status == 'blocked':
        customers = customers.filter(is_blocked=True)
    elif filter_status == 'unblocked':
        customers = customers.filter(is_blocked=False)

    paginator = Paginator(customers, 8)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    return render(request, 'admin/customers.html', {
        'page_obj': page_obj,
        'customers':page_obj.object_list,
        'search_query': search_query,
        'filter_status': filter_status
    })

@login_required(login_url='admin_login')
def toggle_block_status(request, customer_id):
    if request.method=='POST':
        customer =get_object_or_404(User,id=customer_id)
        customer.is_blocked = not customer.is_blocked
        customer.save()
        return JsonResponse({
            'success':True,
            'is_blocked':customer.is_blocked,
            'customer_id':customer.id
        })
    return JsonResponse({'success':False})


@login_required(login_url='admin_login')
def admin_category_list(request):
    search_query=request.GET.get('q','')

    categories = Category.objects.all_with_deleted().order_by('-created_at')

    if search_query:
        categories = categories.filter(Q(name__icontains=search_query))

    paginator = Paginator(categories, 8)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    params = request.GET.copy()

    if "page" in params:
        params.pop("page")  
    querystring = params.urlencode()


    primary_images = {}
    for cat in page_obj:
        if cat.image:
            url , _= cloudinary_url(
                cat.image,
                width=100,
                height=100,
                crop='fill',
                gravity='auto',
                secure=True
            )
            primary_images[cat.id]=url

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'primary_images':primary_images,
        "querystring": querystring,

    }

    return render(request,'admin/category_list.html',context)



@login_required(login_url='admin_login')
def add_category(request):
    if request.method=='POST':
        print("POST:", request.POST)
        print("IMAGE RECEIVED:", request.POST.get("image"))

        form = CategoryForm(request.POST)
        print("FORM ERRORS:", form.errors)

        if form.is_valid():
            form.save()
            return redirect('admin_category_list')
    else:
        form=CategoryForm()
       
    return render(request,'admin/category_form.html',{'form':form})


@login_required(login_url='admin_login')
def edit_category(request,id):
    category =get_object_or_404(Category.objects.all_with_deleted(),id=id)
    if request.method=='POST':
        form = CategoryForm(request.POST or None, instance=category,show_deleted=True)
        if form.is_valid():
            form.save()
            return redirect('admin_category_list')
    else:
        form=CategoryForm(instance=category)

    if category.image:
        category_image_url, _ = cloudinary_url(
        category.image,
        width=300,
        height=300,
        crop="fill",
        secure=True
    )
    else:
        category_image_url = None
        
    context={
        'form':form,
        'category_image_url':category_image_url
    }
    return render(request,'admin/category_form.html',context)


@login_required(login_url='admin_login')
def delete_category(request, id):
    Category.objects.soft_delete(id)
    return redirect('admin_category_list')

@login_required(login_url='admin_login')
@require_POST
def restore_category(request, id):
    category = Category.objects.restore(id)
    if category:
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'message': 'Category not found or already active'})



@login_required(login_url='admin_login')
def admin_product_list(request):

    if request.GET.get('clear'):
        return redirect('admin_product_list')
    
   
    search_query = request.GET.get('q', '').strip()

    
    products = Product.objects.all_with_deleted().prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.order_by('-is_primary', '-created_at'))
    ).order_by('-created_at')

    if search_query:
        products = products.filter(Q(name__icontains=search_query))


    paginator = Paginator(products, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    params = request.GET.copy()
    if "page" in params:
        params.pop("page")
    clean_querystring = params.urlencode()



    primary_images = {}
    for product in page_obj:
        primary_image = product.images.filter(is_primary=True).first() or product.images.first()
        if primary_image and hasattr(primary_image.image, 'url'):
            primary_images[product.id] = primary_image.image.url
        else:
            primary_images[product.id] = None


    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'search_query': search_query,
        'primary_images': primary_images, 
        "querystring": clean_querystring,

    }

    return render(request, 'admin/product_list.html', context)


@login_required(login_url='admin_login')
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        image_urls = json.loads(request.POST.get('images', '[]'))


        if len(image_urls) < 3:
            messages.error(request, "Please upload at least 3 images before saving.")
            return render(request, 'admin/product_form.html', {'form': form})

        if form.is_valid():
            product = form.save()


            for url in image_urls:
                ProductImage.objects.create(product=product, image=url)

            messages.success(request, "Product added successfully.")
            return redirect('admin_variant_list', product_id=product.id)
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ProductForm()

    return render(request, 'admin/product_form.html', {'form': form})



@login_required(login_url='admin_login')
def edit_product(request, id):

    product = get_object_or_404(Product.objects.all_with_deleted(), id=id)

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product, show_deleted=True)
        image_urls = json.loads(request.POST.get('images', '[]'))

        if len(image_urls) < 3:
            messages.error(request, "Please keep at least 3 product images.")
            return render(request, 'admin/product_form.html', {
                'form': form,
                'product': product,
                'existing_images': json.dumps(image_urls),
            })

        if form.is_valid():
            form.save()

            
            existing_images = [
                img.image.url
                for img in ProductImage.objects.filter(product=product)
                if hasattr(img.image, 'url')
            ]

            new_urls = set(image_urls)
            old_urls = set(existing_images)

            
            for removed_url in old_urls - new_urls:
                ProductImage.objects.filter(product=product, image__contains=removed_url).delete()

            
            for added_url in new_urls - old_urls:
                ProductImage.objects.create(product=product, image=added_url)

            messages.success(request, "Product updated successfully.")
            return redirect('admin_product_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm(instance=product, show_deleted=True)


    existing_images = [
        img.image.url
        for img in ProductImage.objects.filter(product=product)
        if hasattr(img.image, 'url')
    ]

    context = {
        'form': form,
        'product': product,
        'existing_images': json.dumps(existing_images),
    }
    return render(request, 'admin/product_form.html', context)


@login_required(login_url='admin_login')
def delete_product(request, id):

    product = Product.objects.soft_delete(id)

    if not product:
        messages.warning(request, "⚠️ This product was already deleted or not found.")
    else:
        messages.success(request, f"🗑️ Product '{product.name}' deleted successfully.")

    return redirect('admin_product_list')



@login_required(login_url='admin_login')
@require_POST
def restore_product(request, id):
    product = Product.objects.restore(id)
    if product:
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'message': 'Product not found or already active'})


@login_required(login_url='admin_login')
def admin_variant_list(request, product_id):

    product = get_object_or_404(Product, id=product_id)
    search_query = request.GET.get('q', '').strip()
    filter_status = request.GET.get('filter', '')


    variants = ProductVariant.objects.all_with_deleted().filter(product=product)


    if search_query:
        variants = variants.filter(material_type__icontains=search_query) 

    if filter_status == 'active':
        variants = variants.filter(is_deleted=False)
    elif filter_status == 'deleted':
        variants = variants.filter(is_deleted=True)


    paginator = Paginator(variants.order_by('-created_at'), 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    params = request.GET.copy()
    if "page" in params:
        params.pop("page")
    clean_querystring = params.urlencode()


    return render(request, 'admin/variant_list.html', {
        'variants': page_obj,
        'page_obj': page_obj,
        'product': product,
        'search_query': search_query,
        'filter_status': filter_status,
        "querystring": clean_querystring,

    })

@login_required(login_url='admin_login')
def add_variant(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        form = ProductVariantForm(request.POST,instance=ProductVariant(product=product))
        if form.is_valid():
            variant = form.save(commit=False)
            variant.product = product  
            variant.save()
            messages.success(request, "Variant added successfully.")
            return redirect('admin_variant_list', product_id=product.id)
    else:
        form = ProductVariantForm()

    return render(request, 'admin/variant_form.html', {
        'form': form,
        'product': product
    })

@login_required(login_url='admin_login')
def edit_variant(request, id):
    variant = get_object_or_404(ProductVariant.objects.all_with_deleted(), id=id)
    product = variant.product  

    if request.method == 'POST':
        form = ProductVariantForm(request.POST, instance=variant,show_deleted=True)
        if form.is_valid():
            form.save()
            messages.success(request, "Variant updated successfully.")
            return redirect('admin_variant_list', product_id=product.id)
    else:
        form = ProductVariantForm(instance=variant,show_deleted=True)

    return render(request, 'admin/variant_form.html', {
        'form': form,
        'variant': variant,
        'product': product
    })

@login_required(login_url='admin_login')
def delete_variant(request, id):
    variant = ProductVariant.objects.soft_delete(id)
    if variant:
        messages.success(request, f"Variant '{variant.material_type}' deleted successfully.")
        return redirect('admin_variant_list', product_id=variant.product.id)
    messages.error(request, "Variant not found.")
    return redirect('admin_product_list')


@login_required(login_url='admin_login')
@require_POST
def restore_variant(request, id):
    variant = ProductVariant.objects.restore(id)
    if variant:
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'message': 'Variant not found or already active.'})


@login_required(login_url='admin_login')
def admin_order_list(request):
    search_query = request.GET.get("q", "")

    orders=Orders.objects.select_related("user","address").order_by("-created_at")

    if search_query:
        orders = orders.filter(order_id__icontains=search_query)

    paginator = Paginator(orders, 10)  
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "admin/order_list.html", {
        "page_obj": page_obj,
        "search_query": search_query,
    })


@login_required(login_url='admin_login')
def admin_order_details(request,order_id):
    order=get_object_or_404(Orders,order_id=order_id)
    items=order.items.select_related("product","product__product")

    if request.method=="POST":
        item_id=request.POST.get("item_id")
        new_status=request.POST.get("status")

        if "payment_status" in request.POST:
            order.is_paid = request.POST["payment_status"]
            order.save()
            messages.success(request, "Payment status updated.")
            return redirect("order_details", order_id=order_id)

        item=get_object_or_404(OrderItem,id=item_id,order=order)
        print("POSTED ITEM ID:", item_id)
        print("NEW STATUS:", new_status)
        item.status=new_status
        item.save()
        messages.success(request,"Order Item status updated successfully.")
        return redirect("order_details",order_id=order_id)
    
    return render(request,"admin/order_details.html",{"order":order,"items":items})