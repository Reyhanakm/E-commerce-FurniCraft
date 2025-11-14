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
from django.forms import inlineformset_factory
from cloudinary.utils import cloudinary_url



from users.models import User,UserManager
from .models import Category,Product,ProductVariant,ProductImage
from .forms import CategoryForm,ProductForm,ProductVariantForm,ProductImageForm




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

    paginator = Paginator(customers, 6)
    page = request.GET.get('page')
    customers = paginator.get_page(page)

    return render(request, 'admin/customers.html', {
        'customers': customers,
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
    categories = Category.objects.all_with_deleted().order_by('-created_at')


    paginator = Paginator(categories, 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

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
        'primary_images':primary_images,
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


# VariantFormSet= inlineformset_factory(Product,ProductVariant,form=ProductVariantForm,extra=1,can_delete=True)

@login_required(login_url='admin_login')
def admin_product_list(request):
    # Clear search query param
    if request.GET.get('clear'):
        return redirect('admin_product_list')
    
    # Search query
    search_query = request.GET.get('q', '').strip()

    # Fetch products (including deleted)
    products = Product.objects.all_with_deleted().prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.order_by('-is_primary', '-created_at'))
    ).order_by('-created_at')

    # Apply search filter if present
    if search_query:
        products = products.filter(Q(name__icontains=search_query))

    # Pagination
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Build dict of primary images for easy lookup in template
    primary_images = {}
    for product in page_obj:
        primary_image = product.images.filter(is_primary=True).first() or product.images.first()
        if primary_image and hasattr(primary_image.image, 'url'):
            primary_images[product.id] = primary_image.image.url
        else:
            primary_images[product.id] = None

    # Context
    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'search_query': search_query,
        'primary_images': primary_images, 
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
    """Edit existing product details and manage images."""
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

            # Handle images
            existing_images = [
                img.image.url
                for img in ProductImage.objects.filter(product=product)
                if hasattr(img.image, 'url')
            ]

            new_urls = set(image_urls)
            old_urls = set(existing_images)

            # Delete removed
            for removed_url in old_urls - new_urls:
                ProductImage.objects.filter(product=product, image__contains=removed_url).delete()

            # Add new
            for added_url in new_urls - old_urls:
                ProductImage.objects.create(product=product, image=added_url)

            messages.success(request, "Product updated successfully.")
            return redirect('admin_product_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm(instance=product, show_deleted=True)

    #  convert CloudinaryResource to URL
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
    """Soft delete a product."""
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
def variant_list(request, product_id):
    """Show all variants for a specific product with search, filter & pagination."""
    product = get_object_or_404(Product, id=product_id)
    search_query = request.GET.get('q', '').strip()
    filter_status = request.GET.get('filter', '')

    # Start from all variants for this product (including deleted)
    variants = ProductVariant.objects.all_with_deleted().filter(product=product)

    # Search by material type
    if search_query:
        variants = variants.filter(material_type__icontains=search_query) 
    # Filter by status
    if filter_status == 'active':
        variants = variants.filter(is_deleted=False)
    elif filter_status == 'deleted':
        variants = variants.filter(is_deleted=True)

    # Pagination
    paginator = Paginator(variants.order_by('-created_at'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin/variant_list.html', {
        'variants': page_obj,
        'page_obj': page_obj,
        'product': product,
        'search_query': search_query,
        'filter_status': filter_status,
    })

@login_required(login_url='admin_login')
def add_variant(request, product_id):
    """Add a new variant for a specific product."""
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        form = ProductVariantForm(request.POST)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.product = product  # assign parent product
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
    """Edit existing variant (including deleted ones)."""
    variant = get_object_or_404(ProductVariant.objects.all_with_deleted(), id=id)
    product = variant.product  # for redirect and context

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
    """Soft delete a variant."""
    variant = ProductVariant.objects.soft_delete(id)
    if variant:
        messages.success(request, f"Variant '{variant.material_type}' deleted successfully.")
        return redirect('admin_variant_list', product_id=variant.product.id)
    messages.error(request, "Variant not found.")
    return redirect('admin_product_list')


@login_required(login_url='admin_login')
@require_POST
def restore_variant(request, id):
    """Restore a soft-deleted variant."""
    variant = ProductVariant.objects.restore(id)
    if variant:
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'message': 'Variant not found or already active.'})

