from decimal import Decimal
import json
import logging

from django.shortcuts import render,redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import login,logout
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q,Prefetch
from cloudinary.utils import cloudinary_url
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.utils.timezone import now
from datetime import timedelta, timezone
from openpyxl import Workbook


from admin_app.services.sales_report import get_date_range, get_sold_items
from commerce.utils.coupons import calculate_item_coupon_share

from .forms import BannerForm
from .models import Banner
from commerce.models import Orders,OrderItem,OrderReturn
from users.models import User,UserManager
from product.models import Category,Product,ProductVariant,ProductImage,ProductOffer,CategoryOffer,Coupon,CouponUsage
from product.forms import CategoryForm,ProductForm,ProductVariantForm,ProductOfferForm,CategoryOfferForm,CouponForm
from commerce.utils.orders import is_first_successful_order
from commerce.utils.referral import process_referral_after_first_order 
from commerce.services.returns import approve_return_service
from .services.order_status import update_order_payment_status,update_order_item_status

logger = logging.getLogger("admin_app")


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
def admin_order_details(request, order_id):
    order = get_object_or_404(Orders, order_id=order_id)
    items = order.items.select_related("product", "product__product")

    if request.method == "POST":

        # PAYMENT STATUS UPDATE
        if "payment_status" in request.POST:
            new_payment_status = request.POST["payment_status"]

            logger.info(
                f"[ADMIN] {request.user.email} updating payment status "
                f"Order={order.order_id} Status={new_payment_status}"
            )

            try:
                update_order_payment_status(order, new_payment_status)
                messages.success(request, "Payment status updated.")
            except ValidationError as e:
                logger.warning(
                    f"[PAYMENT BLOCKED] Order={order.order_id} Reason={str(e)}"
                )
                messages.error(request, str(e))

            return redirect("order_details", order_id=order_id)

        # ITEM STATUS UPDATE
        item_id = request.POST.get("item_id")
        new_status = request.POST.get("status")

        item = get_object_or_404(OrderItem, id=item_id, order=order)

        logger.info(
            f"[ADMIN] {request.user.email} attempting item status update "
            f"Order={order.order_id} Item={item.id} "
            f"From={item.status} To={new_status}"
        )

        try:
            update_order_item_status(item, new_status)
            messages.success(request, "Order item status updated successfully.")

            logger.info(
                f"[ITEM UPDATED] Order={order.order_id} "
                f"Item={item.id} Status={new_status}"
            )

        except ValidationError as e:
            logger.warning(
                f"[ITEM UPDATE BLOCKED] Order={order.order_id} "
                f"Item={item.id} Reason={str(e)}"
            )
            messages.error(request, str(e))

        return redirect("order_details", order_id=order_id)

    return render(
        request,
        "admin/order_details.html",
        {"order": order, "items": items}
    )
@require_POST
@staff_member_required(login_url='admin_login')
def approve_return(request, return_id):
    return_request = get_object_or_404(
        OrderReturn,
        id=return_id,
        approval_status="pending"
    )

    refund_amount = approve_return_service(return_request)

    messages.success(
        request,
        f"Return approved. ₹{refund_amount} refunded to wallet."
    )

    return redirect("admin_return_list")

@require_POST
@staff_member_required(login_url="admin_login")
def reject_return(request, return_id):
    return_request = get_object_or_404(
        OrderReturn,
        id=return_id,
        approval_status="pending"
    )

    admin_note = request.POST.get("admin_note", "").strip()

    return_request.approval_status = "rejected"
    return_request.admin_note = admin_note
    return_request.save(update_fields=["approval_status", "admin_note"])

    messages.success(request, "Return request rejected.")
    return redirect("admin_return_list")
  
@staff_member_required(login_url='admin_login')
def admin_return_list(request):
    returns = (
        OrderReturn.objects
        .select_related("user", "item__order")
        .order_by("approval_status", "-created_at")
    )

    return render(
        request,
        "admin/returns/return_list.html",
        {"returns": returns}
    )


@login_required(login_url='admin_login')
def create_product_offer(request):
    if request.method=='POST':
        ProductOffer.objects.create(
            name=request.POST.get('name'),
            product_id=request.POST['product'],
            discount_type=request.POST['discount_type'],
            discount_value=request.POST['discount_value'],
            max_discount_amount=request.POST.get('max_discount_amount') or None,
            start_date=request.POST['start_date'],
            end_date=request.POST['end_date'],
            is_active=True
        )
        messages.success(request,"Product offer created.")
        return redirect('admin_product_offer_list')


@login_required(login_url='admin_login')
def admin_offer_list(request):
    search_query = request.GET.get("q", "").strip()

    product_offers = ProductOffer.objects.all().order_by("-created_at")
    category_offers = CategoryOffer.objects.all().order_by("-created_at")

    if search_query:
        product_offers = product_offers.filter(
            Q(name__icontains=search_query) |
            Q(product__name__icontains=search_query)
        )
        category_offers = category_offers.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    paginator = Paginator(product_offers,8)
    page_number = request.GET.get("page")
    product_page_obj = paginator.get_page(page_number)


    params = request.GET.copy()
    if "page" in params:
        params.pop("page")
    clean_querystring = params.urlencode()

    return render(request, "admin/offers/offer_list.html", {
        "product_offers": product_page_obj,
        "category_offers": category_offers,
        "page_obj": product_page_obj,
        "search_query": search_query,
        "querystring": clean_querystring,
    })

@login_required(login_url='admin_login')
def admin_offer_create(request):
    offer_type = request.POST.get("offer_type") or request.GET.get("type") or "product"

    if offer_type == "product":
        product_form = ProductOfferForm(request.POST or None)
        category_form = None
    else:
        product_form = None
        category_form = CategoryOfferForm(request.POST or None)

    if request.method == "POST":
        if offer_type == "product" and product_form.is_valid():
            product_form.save()
            messages.success(request, "Product offer created successfully.")
            return redirect("admin_offer_list")

        if offer_type == "category" and category_form.is_valid():
            category_form.save()
            messages.success(request, "Category offer created successfully.")
            return redirect("admin_offer_list")

    return render(request, "admin/offers/offer_form.html", {
        "title": "Add Offer",
        "show_offer_type": True,
        "offer_type": offer_type,
        "product_form": product_form,
        "category_form": category_form,
    })

@login_required(login_url='admin_login')
def admin_product_offer_edit(request, pk):
    offer = get_object_or_404(ProductOffer, pk=pk)
    form = ProductOfferForm(request.POST or None, instance=offer)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product offer updated.")
        return redirect("admin_offer_list")

    return render(request, "admin/offers/offer_form.html", {
        "title": "Edit Product Offer",
        "show_offer_type": False,   
        "offer_type": "product",
        "product_form": form,      
        "category_form": None,      
    })

@login_required(login_url='admin_login')
def admin_category_offer_edit(request, pk):
    offer = get_object_or_404(CategoryOffer, pk=pk)
    form = CategoryOfferForm(request.POST or None, instance=offer)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Category offer updated.")
        return redirect("admin_offer_list")

    return render(request, "admin/offers/offer_form.html", {
        "title": "Edit Category Offer",
        "show_offer_type": False,   
        "offer_type": "category",
        "product_form": None,
        "category_form": form,
    })

@login_required(login_url='admin_login')
@require_POST
def admin_offer_toggle(request, offer_type, pk):
    model = ProductOffer if offer_type == "product" else CategoryOffer
    offer = get_object_or_404(model, pk=pk)

    offer.is_active = not offer.is_active
    offer.save(update_fields=["is_active"])

    status = "activated" if offer.is_active else "deactivated"
    messages.success(request, f"Offer {status} successfully.")
    return redirect("admin_offer_list")


@login_required(login_url="admin_login")
def admin_coupon_list(request):
    coupons = (
        Coupon.objects
        .filter(is_deleted=False)
        .annotate(used_count=Count("usages"),per_user_count=Count('coupon_usages'))
        .order_by("-created_at")
    )

    return render(request, "admin/coupons/list.html", {
        "coupons": coupons
    })

@login_required(login_url="admin_login")
def admin_coupon_create(request):
    form = CouponForm(request.POST or None)

    if form.is_valid():
        form.save()
        messages.success(request, "Coupon created successfully")
        return redirect("admin_coupon_list")

    return render(request, "admin/coupons/form.html", {
        "form": form,
        "title": "Create Coupon"
    })

@login_required(login_url="admin_login")
def admin_coupon_edit(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk, is_deleted=False)
    form = CouponForm(request.POST or None, instance=coupon)

    if form.is_valid():
        form.save()
        messages.success(request, "Coupon updated successfully")
        return redirect("admin_coupon_list")

    return render(request, "admin/coupons/form.html", {
        "form": form,
        "title": "Edit Coupon"
    })
@login_required(login_url="admin_login")
def admin_coupon_toggle(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.is_active = not coupon.is_active
    coupon.save(update_fields=["is_active"])

    messages.success(request, "Coupon status updated")
    return redirect("admin_coupon_list")

@login_required(login_url="admin_login")
def admin_coupon_delete(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.is_deleted = True
    coupon.is_active = False
    coupon.save(update_fields=["is_deleted", "is_active"])

    messages.success(request, "Coupon deleted")
    return redirect("admin_coupon_list")


@login_required(login_url="admin_login")
def sales_report(request):

    range_type = request.GET.get("range")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    start, end = get_date_range(range_type, start_date, end_date)

    sold_items = get_sold_items(start, end)

    total_sales = Decimal("0.00")
    product_discount = Decimal("0.00")
    coupon_discount = Decimal("0.00")

    for item in sold_items:
        total_sales += item.price
        product_discount += (item.unit_price * item.quantity) - item.price
        coupon_discount += calculate_item_coupon_share(item.order, item)

    context = {
        "sold_items": sold_items,
        "order_count": sold_items.values("order_id").distinct().count(),
        "total_sales": total_sales,
        "product_discount": product_discount,
        "coupon_discount": coupon_discount,
        "overall_discount": product_discount + coupon_discount,
        "start_date": start,
        "end_date": end,
        "range_type": range_type,
    }

    return render(request, "admin/sales_report.html", context)


@login_required(login_url="admin_login")
def sales_report_excel(request):

  
    range_type = request.GET.get("range")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    start, end = get_date_range(range_type, start_date, end_date)

    sold_items = get_sold_items(start, end)

   
    wb = Workbook()
    ws = wb.active
    ws.title = "Sales Report"

    headers = [
        "Order ID",
        "Order Date",
        "Product",
        "Quantity",
        "Net Price",
        "Product Discount",
        "Coupon Discount",
    ]
    ws.append(headers)


    total_sales = Decimal("0.00")
    product_discount = Decimal("0.00")
    coupon_discount = Decimal("0.00")

    for item in sold_items:
        prod_discount = (item.unit_price * item.quantity) - item.price
        coup_discount = calculate_item_coupon_share(item.order, item)

        ws.append([
            item.order.order_id,
            item.order.created_at.strftime("%Y-%m-%d"),
            str(item.product),
            item.quantity,
            float(item.price),
            float(prod_discount),
            float(coup_discount),
        ])

        total_sales += item.price
        product_discount += prod_discount
        coupon_discount += coup_discount

    ws.append([])
    ws.append(["TOTAL SALES", "", "", "", float(total_sales), "", ""])
    ws.append(["PRODUCT DISCOUNT", "", "", "", "", float(product_discount), ""])
    ws.append(["COUPON DISCOUNT", "", "", "", "", "", float(coupon_discount)])
    ws.append([
        "OVERALL DISCOUNT", "", "", "", "",
        float(product_discount + coupon_discount), ""
    ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="sales_report.xlsx"'

    wb.save(response)
    return response
