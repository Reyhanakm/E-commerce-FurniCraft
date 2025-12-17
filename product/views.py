from django.shortcuts import render, redirect,HttpResponse,get_object_or_404
from product.models import Category,Product,ProductImage,ProductVariant
from django.db.models import Prefetch,Q,Min
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from users.models import User
from django.core.cache import cache
from commerce.models import Wishlist, WishlistItem
import json
from users.decorators import block_check
from commerce.pricing import get_pricing_context



# @block_check
# @login_required
# def category_products(request,id):
#     category=Category.objects.get(id=id)
#     products=Product.objects.filter(category=category).prefetch_related(
#         Prefetch('variants',queryset=ProductVariant.objects.order_by('id')),
#         Prefetch('images',queryset=ProductImage.objects.order_by('-is_primary','id')))
    
#     return render(request,'product/category_products.html',{'products':products,'category':category})
# product/views.py


@block_check
@login_required 
def category_products(request, id):
    category = get_object_or_404(Category, id=id)
    
    # Efficiently fetch Products and related data
    products = Product.objects.filter(category=category).prefetch_related(
        Prefetch('variants', queryset=ProductVariant.objects.order_by('id')),
        Prefetch('images', queryset=ProductImage.objects.order_by('-is_primary', 'id'))
    )
    
    # --- WISHILIST CONTEXT LOGIC (NEW) ---
    wishlist_product_ids = set()
    
    if request.user.is_authenticated:
        # 1. Fetch the IDs of the parent Products (Product.id) that are in the user's wishlist.
        #    We filter WishlistItem by the current user and get the ID of the linked Product (via ProductVariant).
        #    We use .values_list and set() for maximum efficiency.
        wishlist_product_ids = set(
            WishlistItem.objects.filter(
                wishlist__user=request.user,
                # Filter to only check products currently displayed on the page (optional optimization)
                product__product__in=products 
            ).values_list('product__product__id', flat=True)
        )
    # --------------------------------------

    context = {
        'products': products,
        'category': category,
        'wishlist_product_ids': wishlist_product_ids # <-- Pass the set of IDs to the template
    }
    
    return render(request, 'product/category_products.html', context)

# @block_check
# @never_cache
# @login_required(login_url="/login")
# def products(request):    
#     products=Product.objects.filter(category__is_deleted=False,variants__isnull=False).annotate(min_price=Min('variants__sales_price')).prefetch_related(
#         Prefetch('images',queryset=ProductImage.objects.order_by('id')),
#         Prefetch('variants',queryset=ProductVariant.objects.order_by('id')))
    
#     search_query = request.GET.get('search')

#     if search_query:
#         products=products.filter(Q(name__icontains=search_query)|Q(category__name__icontains=search_query)|
#                         Q(variants__material_type__icontains=search_query))

#     category_ids = request.GET.getlist('category')
#     if category_ids:
#         products = products.filter(category_id__in=category_ids)

#     price_min = request.GET.get('price_min')
#     price_max = request.GET.get('price_max')

#     price_options = [
#     ("0-4999", "₹0 – ₹4,999"),
#     ("5000-24999", "₹5,000 – ₹24,999"),
#     ("25000-49999", "₹25,000 – ₹49,999"),
#     ("50000-99999", "₹50,000 – ₹99,999"),
#     ("100000-9999999", "₹100,000+"),
# ]
#     selected_price_ranges=request.GET.getlist('price_range')

#     if price_min:
#         products = products.filter(min_price__gte=price_min)
#     if price_max:
#         products = products.filter(min_price__lte=price_max)

#     selected_price_ranges=[pr for pr in selected_price_ranges if pr and '-' in pr]
#     if selected_price_ranges:
#         price_query=Q()
#         for pr in selected_price_ranges:
#             low,high=pr.split('-')
#             price_query |=Q(min_price__gte=low,min_price__lte=high)
#         products= products.filter(price_query)
    

#     sort = request.GET.get('sort')
#     if sort == 'low_to_high':
#         products = products.order_by('min_price')
#     elif sort == 'high_to_low':
#         products = products.order_by('-min_price')
#     elif sort == 'a_to_z':
#         products = products.order_by('name')
#     elif sort == 'z_to_a':
#         products = products.order_by('-name')
#     elif sort == 'new':
#         products = products.order_by('-created_at')
    
#     if not sort:
#         products = products.order_by('id')


#     paginator = Paginator(products, 8)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)

#     params = request.GET.copy()
#     if "page" in params:
#         params.pop("page")
#     querystring = params.urlencode()

#     context = {
#         "page_obj": page_obj,
#         "products": page_obj.object_list,
#         "categories": Category.objects.all(),
#         "price_options": price_options,
#         "selected_price_ranges":selected_price_ranges,
#         "search": search_query,
#         "querystring": querystring,
#     }


#     if request.headers.get("HX-Request"):
#         return render(request, "product/components/product_list_partial.html", context)


#     return render(request, "product/products.html", context)

@block_check
@never_cache
@login_required(login_url="/login")
def products(request):    

    products = Product.objects.filter(
        category__is_deleted=False,
        variants__isnull=False
    ).annotate(
        min_price=Min('variants__sales_price')  
    ).prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.order_by('id')),
        Prefetch('variants', queryset=ProductVariant.objects.order_by('id'))
    )

    search_query = request.GET.get('search')

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(variants__material_type__icontains=search_query)
        )

    category_ids = request.GET.getlist('category')
    if category_ids:
        products = products.filter(category_id__in=category_ids)

    # -------- PRICE FILTERS (KEEP AS IS) --------
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')

    if price_min:
        products = products.filter(min_price__gte=price_min)
    if price_max:
        products = products.filter(min_price__lte=price_max)

    selected_price_ranges = request.GET.getlist('price_range')
    selected_price_ranges = [pr for pr in selected_price_ranges if pr and '-' in pr]

    if selected_price_ranges:
        price_query = Q()
        for pr in selected_price_ranges:
            low, high = pr.split('-')
            price_query |= Q(min_price__gte=low, min_price__lte=high)
        products = products.filter(price_query)

    # -------- SORTING (KEEP AS IS) --------
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
    else:
        products = products.order_by('id')

    paginator = Paginator(products, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # -------- NEW: SAFE OFFER PRICE INJECTION --------
    from commerce.pricing import get_pricing_context

    for product in page_obj.object_list:
        prices = []
        for variant in product.variants.all():
            ctx = get_pricing_context(variant)
            prices.append(ctx["current_price"])

        # dynamic price (offer aware)
        product.display_price = min(prices) if prices else product.min_price

    params = request.GET.copy()
    if "page" in params:
        params.pop("page")
    querystring = params.urlencode()

    context = {
        "page_obj": page_obj,
        "products": page_obj.object_list,
        "categories": Category.objects.all(),
        "price_options": [
            ("0-4999", "₹0 – ₹4,999"),
            ("5000-24999", "₹5,000 – ₹24,999"),
            ("25000-49999", "₹25,000 – ₹49,999"),
            ("50000-99999", "₹50,000 – ₹99,999"),
            ("100000-9999999", "₹100,000+"),
        ],
        "selected_price_ranges": selected_price_ranges,
        "search": search_query,
        "querystring": querystring,
    }

    if request.headers.get("HX-Request"):
        return render(
            request,
            "product/components/product_list_partial.html",
            context
        )

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

    is_in_wishlist = False
    if request.user.is_authenticated:
        
        default_variant = product.variants.first()
        
        if default_variant:
            is_in_wishlist = WishlistItem.objects.filter(
                wishlist__user=request.user,
                product=default_variant 
            ).exists()
    return render(request,'product/product_details.html',{'product':product,'related_products':related_products,
                                        'is_in_wishlist': is_in_wishlist,
                                        'default_variant_id': product.variants.first().id 
                                        if product.variants.first() else None,
    })

@block_check
def load_product_image(request, id):
    src = request.GET.get("src")
    return HttpResponse(f"""
        <img src='{src}' class='zoomable w-full h-auto rounded-xl shadow-lg object-cover'>
    """)
# @block_check
# def load_variant_info(request, variant_id):
#     v = ProductVariant.objects.get(id=variant_id)
#     return render(request,'product/components/variant_info.html',{'variant':v})


@block_check
def load_variant_info(request, variant_id):
    # 1. Get the variant
    v = ProductVariant.objects.get(id=variant_id)
    
    # 2. Check if it's in the wishlist (Default to False)
    is_in_wishlist = False
    
    if request.user.is_authenticated:
        # Check if a WishlistItem exists for this user and this variant
        # We query across the relationship: wishlist -> user
        is_in_wishlist = WishlistItem.objects.filter(
            wishlist__user=request.user, 
            product=v
        ).exists()

    # 3. Pass the boolean to the template
    context = {
        'variant': v,
        'is_in_wishlist': is_in_wishlist
    }
    
    return render(request, 'product/components/variant_info.html', context)