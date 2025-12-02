from django.shortcuts import render, redirect,HttpResponse
from product.models import Category,Product,ProductImage,ProductVariant
from django.db.models import Prefetch,Q,Min
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from users.models import User
from django.core.cache import cache
import json
from users.decorators import block_check


@block_check
@login_required
def category_products(request,id):
    category=Category.objects.get(id=id)
    products=Product.objects.filter(category=category).prefetch_related(
        Prefetch('variants',queryset=ProductVariant.objects.order_by('id')),
        Prefetch('images',queryset=ProductImage.objects.order_by('-is_primary','id')))
    
    return render(request,'product/category_products.html',{'products':products,'category':category})


@block_check
@never_cache
@login_required(login_url="/login")
def products(request):    
    products=Product.objects.filter(category__is_deleted=False).annotate(min_price=Min('variants__sales_price')).prefetch_related(
        Prefetch('images',queryset=ProductImage.objects.order_by('id')),
        Prefetch('variants',queryset=ProductVariant.objects.order_by('id')))
    
    search_query = request.GET.get('search')

    if search_query:
        products=products.filter(Q(name__icontains=search_query)|Q(category__name__icontains=search_query)|
                        Q(variants__material_type__icontains=search_query))

    category_ids = request.GET.getlist('category')
    if category_ids:
        products = products.filter(category_id__in=category_ids)

    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')

    price_options = [
    ("0-4999", "₹0 – ₹4,999"),
    ("5000-24999", "₹5,000 – ₹24,999"),
    ("25000-49999", "₹25,000 – ₹49,999"),
    ("50000-99999", "₹50,000 – ₹99,999"),
    ("100000-9999999", "₹100,000+"),
]
    selected_price_ranges=request.GET.getlist('price_range')

    if price_min:
        products = products.filter(min_price__gte=price_min)
    if price_max:
        products = products.filter(min_price__lte=price_max)

    selected_price_ranges=[pr for pr in selected_price_ranges if pr and '-' in pr]
    if selected_price_ranges:
        price_query=Q()
        for pr in selected_price_ranges:
            low,high=pr.split('-')
            price_query |=Q(min_price__gte=low,min_price__lte=high)
        products= products.filter(price_query)
    

    sort = request.GET.get('sort')
    if sort == 'low_to_high':
        products = products.order_by('min_price')
    elif sort == 'high_to_low':
        products = products.order_by('-min_price')
    elif sort == 'a_to_z':
        products = products.order_by('name')
    elif sort == 'z_to_a':
        products = products.order_by('-name')
    elif sort == 'new':
        products = products.order_by('-created_at')
    
    if not sort:
        products = products.order_by('id')


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
        "categories": Category.objects.all(),
        "price_options": price_options,
        "selected_price_ranges":selected_price_ranges,
        "search": search_query,
        "querystring": querystring,
    }


    if request.headers.get("HX-Request"):
        return render(request, "product/components/product_list_partial.html", context)


    return render(request, "product/products.html", context)

@block_check
@never_cache
@login_required(login_url='/login')
def product_details(request,id):
    product=Product.objects.select_related('category').prefetch_related(
        Prefetch('images',queryset=ProductImage.objects.order_by('-is_primary','id')),
        'variants'
    ).get(id=id)
    related_products=Product.objects.filter(category=product.category).prefetch_related(
        Prefetch('images',queryset=ProductImage.objects.order_by('-is_primary','id')),
        'variants'
    ).exclude(id=id)
    return render(request,'product/product_details.html',{'product':product,'related_products':related_products})

@block_check
def load_product_image(request, id):
    src = request.GET.get("src")
    return HttpResponse(f"""
        <img src='{src}' class='zoomable w-full h-auto rounded-xl shadow-lg object-cover'>
    """)
@block_check
def load_variant_info(request, variant_id):
    v = ProductVariant.objects.get(id=variant_id)
    return render(request,'product/components/variant_info.html',{'variant':v})


