import logging
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
from commerce.utils.pricing import get_pricing_context,attach_best_pricing_to_products

logger = logging.getLogger('product')

@block_check
@login_required
def category_products(request, id):
    category = get_object_or_404(Category, id=id)
    logger.info(
    "Category products page accessed",
    extra={
        "user_id": request.user.id,
        "category_id": id
    }
    )
    products = Product.objects.filter(category=category,variants__isnull=False).prefetch_related(
        Prefetch(
            'variants',
            queryset=ProductVariant.objects
                .select_related('product__category')
                .prefetch_related(
                    'product__product_offers',
                    'product__category__category_offers'
                )
                .order_by('id')
        ),
        Prefetch(
            'images',
            queryset=ProductImage.objects.order_by('-is_primary', 'id')
        )
    ).distinct()
    logger.info(
    "Products fetched for category",
    extra={
        "category_id": id,
        "product_count": products.count()
    }
    )
    try:
        attach_best_pricing_to_products(products)
    except Exception:
        logger.error(
            "Failed to attach pricing for category products",
            exc_info=True,
            extra={"category_id": id}
        )


    wishlist_product_ids = []

    if request.user.is_authenticated:
        wishlist_product_ids = list(
            WishlistItem.objects.filter(
                wishlist__user=request.user,
                product__product__in=products
            ).values_list(
                'product_id',
                flat=True
            )
        )

    context = {
        'products': products,
        'category': category,
        'wishlist_product_ids': wishlist_product_ids,
    }

    return render(request, 'product/category_products.html', context)

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
        Prefetch('variants', queryset=ProductVariant.objects
            .select_related('product__category')
            .prefetch_related(
                'product__product_offers',
                'product__category__category_offers'
            ))
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
    # filtering
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
    # sorting
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

    wishlist_variant_ids = []
    if request.user.is_authenticated:
        wishlist_variant_ids = list(
            WishlistItem.objects.filter(
                wishlist__user=request.user
            ).values_list("product_id", flat=True)
        )
    logger.info(
    "Product listing accessed",
    extra={
        "user_id": request.user.id,
        "search": search_query,
        "categories": category_ids,
        "sort": sort
    }
    )
    paginator = Paginator(products, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)


    try:
        attach_best_pricing_to_products(page_obj.object_list)
    except Exception:
        logger.error(
            "Pricing injection failed on product list",
            exc_info=True
        )


    params = request.GET.copy()
    if "page" in params:
        params.pop("page")
    querystring = params.urlencode()

    context = {
        "page_obj": page_obj,
        "products": page_obj.object_list,
        "wishlist_product_ids": wishlist_variant_ids,
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
    logger.info(
    "Product pagination",
    extra={
        "page": page_number,
        "total_products": paginator.count
    }
    )
    if request.headers.get("HX-Request"):
        logger.info(
            "HTMX product list request",
            extra={"user_id": request.user.id}
        )



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
    logger.info(
    "Product detail viewed",
    extra={
        "user_id": request.user.id,
        "product_id": id
    }
    )
    try:
        product=Product.objects.select_related('category').prefetch_related(
            Prefetch('images',queryset=ProductImage.objects.order_by('-is_primary','id')),
            'variants',
            'variants__product__product_offers',
            'variants__product__category__category_offers',
        ).get(id=id)
    except Product.DoesNotExist:
        messages.error(request, "This product is temporarily unavailable!")
        return redirect("products")
    related_products=Product.objects.filter(category=product.category).exclude(id=id).prefetch_related(
        Prefetch('images',queryset=ProductImage.objects.order_by('-is_primary','id')),
        'variants',
        'variants__product__product_offers',
        'variants__product__category__category_offers',
    )
    if related_products:
        related_products = list(related_products)
        attach_best_pricing_to_products(related_products)
    is_in_wishlist = False
    wishlist_variant_ids=[]
    if request.user.is_authenticated:
        logger.debug(
            "Wishlist status checked",
            extra={
                "user_id": request.user.id,
                "product_id": id,
                "in_wishlist": is_in_wishlist
            }
        )
        variants=list(product.variants.all())
        default_variant = variants[0] if variants else None
        pricing=get_pricing_context(default_variant) if default_variant else None
        wishlist_variant_ids = list(
            WishlistItem.objects.filter(
                wishlist__user=request.user
            ).values_list("product_id", flat=True)
        )
        if not product.variants.exists():
            logger.warning(
                "Product has no variants",
                extra={"product_id": id}
            )

        if default_variant:
            is_in_wishlist = WishlistItem.objects.filter(
                wishlist__user=request.user,
                product=default_variant 
            ).exists()
    
    return render(request,'product/product_details.html',{'product':product,
                                        'related_products':related_products,
                                        'is_in_wishlist': is_in_wishlist,
                                        'pricing':pricing,
                                        'wishlist_variant_ids': wishlist_variant_ids,
                                        'default_variant': default_variant,
                                        'default_variant_id': default_variant.id if default_variant else None
    })

@block_check
def load_product_image(request, id):
    src = request.GET.get("src")
    logger.debug(
    "Product image loaded dynamically",
    extra={"src": src}
    )
    return HttpResponse(f"""
        <img src='{src}' class='zoomable w-full h-auto rounded-xl shadow-lg object-cover'>
    """)

@block_check
def load_variant_info(request, variant_id):

    logger.info(
    "Variant info loaded",
    extra={
        "variant_id": variant_id,
        "user_id": request.user.id if request.user.is_authenticated else None
    }
    )
    v = ProductVariant.objects.get(id=variant_id)
    try:
        pricing = get_pricing_context(v)
    except Exception:
        logger.error(
            "Variant pricing failed",
            exc_info=True,
            extra={"variant_id": variant_id}
        )

    is_in_wishlist = False
    
    if request.user.is_authenticated:
        is_in_wishlist = WishlistItem.objects.filter(
            wishlist__user=request.user, 
            product=v
        ).exists()

    context = {
        'variant': v,
        'is_in_wishlist': is_in_wishlist,
        'pricing':pricing
    }
    return render(request, 'product/components/variant_info.html', context)