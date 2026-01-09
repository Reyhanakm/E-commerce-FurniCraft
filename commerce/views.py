from django.utils import timezone
import logging
from django.shortcuts import render,redirect,get_object_or_404
from django.db import transaction
from django.db.models import Q,Count
from django.urls import reverse
import json
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache,cache_control
from django.core.paginator import Paginator
from urllib.parse import urlencode
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from commerce.services.exceptions import InsufficientWalletBalance
from commerce.utils.offers import get_discount_percentage
from users.decorators import block_check
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from .models import Cart,CartItem,OrderItem,Orders,Wishlist,WishlistItem,Wallet,WalletTransaction,OrderReturn
from users.models import User,UserAddress
from product.models import Category, Coupon, CouponUsage,Product,ProductVariant
from .utils.trigger import trigger,attach_trigger
from decimal import Decimal
from commerce.utils.pricing import get_pricing_context
from .utils.checkout import render_checkout_summary
from commerce.utils.coupons import validate_and_calculate_coupon,calculate_item_coupon_share
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle,Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from .utils.pdf_styles import get_invoice_styles
from .services.wallet import pay_using_wallet

logger = logging.getLogger("commerce")


def load_wishlist_items(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)

    wishlist_items = (
        WishlistItem.objects
        .filter(wishlist=wishlist)
        .select_related("product", "product__product")
        .prefetch_related(
            "product__product__product_offers",
            "product__product__category__category_offers",
        )
    )

    wishlist_data = []
    for item in wishlist_items:
        variant = item.product
        pricing = get_pricing_context(variant)

        wishlist_data.append({
            "variant": variant,
            "pricing": pricing,
        })

    return render(
        request,
        "commerce/wishlist/wishlist_items.html",
        {"wishlist_data": wishlist_data}
    )

@block_check
@login_required
def wishlist(request):
    return render(request, "commerce/wishlist/wishlist.html", {})


@block_check
@login_required
def toggle_wishlist(request, p_id):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    variant = get_object_or_404(ProductVariant, id=p_id)
    
    item_qs = WishlistItem.objects.filter(wishlist=wishlist, product=variant)
    
    if item_qs.exists():
        item_qs.delete()
        
        icon_html = '<i class="far fa-heart"></i>' 
        
        message = f"{variant.product.name} removed from wishlist."
        toast_type = "warning" 
        
    else:
        WishlistItem.objects.create(wishlist=wishlist, product=variant)
        
        icon_html = '<i class="fas fa-heart text-red-500"></i>'
        
        message = f"{variant.product.name} added to wishlist!"
        toast_type = "success" 
    response = HttpResponse(icon_html, status=200)

    header_data = {
        "toast": {
            "message": message,
            "type": toast_type  
        },
        "wishlistUpdated": True 
    }
    response["HX-Trigger"] = json.dumps(header_data)
    
    return response


@block_check
@login_required
@transaction.atomic 
def move_to_cart(request, p_id):
    """Moves an item from the wishlist to the cart."""
    variant = get_object_or_404(ProductVariant, id=p_id)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)

    cart_response = add_to_cart_logic(request, variant.product, variant)
    
    if cart_response.status_code == 204:
        wishlist_item_qs = WishlistItem.objects.filter(wishlist=wishlist, product=variant)
        wishlist_item_qs.delete()
        
        header_data = json.loads(cart_response["HX-Trigger"])
        
        header_data["wishlistUpdated"] = True
        cart_response["HX-Trigger"] = json.dumps(header_data)
        
        return cart_response
        
    else:
        return cart_response
    

@block_check
@login_required
def wishlist_count(request):
    if not request.user.is_authenticated:
        return HttpResponse("0")

    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    
    count = wishlist.wishlist_items.count() 

    return HttpResponse(count)


@block_check
@login_required
def add_cart_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True, is_deleted=False)
    variant = product.variants.filter(is_deleted=False).first()
    return add_to_cart_logic(request, product, variant)

@block_check
@login_required
def add_cart_variant(request, variant_id):

    variant = get_object_or_404(ProductVariant, id=variant_id, is_deleted=False)
    product = variant.product

    return add_to_cart_logic(request, product, variant)

@block_check
@login_required
def add_to_cart_logic(request, product, variant):
    quantity = 1

    if variant.stock < 1:
        return trigger("Product is out of stock.", "error")

    cart, _ = Cart.objects.get_or_create(user=request.user)
    item = CartItem.objects.filter(cart=cart, variant=variant).first()

    if item:
        if item.quantity + quantity > variant.stock:
            return trigger("Only limited stock available.", "error")
        if item.quantity + quantity > 5:
           return trigger("Cannot add more than 5 per order.", "error")
        
        item.quantity += quantity
        item.save()
        return trigger("Quantity updated in cart!", "success", update=True)

    CartItem.objects.create(cart=cart, product=product, variant=variant, quantity=quantity)
    return trigger("Product added to cart!", "success", update=True)

@block_check
@login_required    
def cart_page(request):

    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related("product", "variant").all()
    deleted_items=cart.items.filter(Q(product__is_deleted=True)|Q(variant__is_deleted=True)|Q(product__category__is_deleted=True))
    if deleted_items.exists():
        deleted_items.delete()
        messages.error(request,"Some items in your cart are no longer availabe and were removed.")
        return redirect("cart_page")

    validation_required = False
    
    for item in list(cart_items): 
        
        if item.variant.stock == 0:
            item.delete()
            messages.error(request, f"'{item.product.name}-({item.variant.material_type})' is now out of stock.Removed from your cart!")
            validation_required = True
            
        elif item.quantity > item.variant.stock:
            old_quantity = item.quantity
            item.quantity = item.variant.stock
            item.save()
            messages.warning(request, 
                f"Quantity reduced! for '{item.product.name}'. Max available stock is now {item.variant.stock}."
            )
            validation_required = True
            
    
    if validation_required:
        return redirect('cart_page')
    for item in cart_items:
        item.offer_percent=get_discount_percentage(item.variant)
        price=Decimal(item.variant.sales_price)
        if item.offer_percent>0:
            item.discounted_price=price-(price* Decimal(item.offer_percent)/100)
            item.offer_percent=round(item.offer_percent)
        else:
            item.discounted_price=price

    return render(request, "commerce/cart/cart_page.html", {
        "cart": cart,
        "cart_items": cart_items,
    })

# for product details page
@block_check
@login_required
def stock_status_for_variant(request, variant_id):
    
    variant = get_object_or_404(ProductVariant, id=variant_id, is_deleted=False)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item = cart.items.filter(variant=variant).first()
    
    in_cart_qty = cart_item.quantity if cart_item else 0

    max_addable_qty = 5 
    
    remaining_stock_in_db = variant.stock - in_cart_qty
    remaining_stock_to_add = max_addable_qty - in_cart_qty
    
    available_to_add = max(0, min(remaining_stock_in_db, remaining_stock_to_add))
    
    context = {
        'variant': variant,
        'in_cart_qty': in_cart_qty,
        'available_to_add': available_to_add,
        'total_stock': variant.stock, 
    }   
    return render(request, "commerce/product/_stock_status.html", context)


@block_check
@login_required
def increase_quantity(request, item_id):

    item = get_object_or_404(
        CartItem.objects.select_related("product", "variant", "cart"),
        id=item_id,
        cart__user=request.user
    )

    if item.quantity < item.variant.stock and item.quantity < 5:
        item.quantity += 1
        item.save()
        message="Quantity Increased."
    else:
        message = "Maximum quantity reached (5) or out of stock."
    data = {
        "toast": {"message": message, "type": "info"},
        "update-cart": True 
    }
    item.offer_percent = get_discount_percentage(item.variant)

    price = Decimal(item.variant.sales_price)
    if item.offer_percent > 0:
        item.discounted_price = price - (price * Decimal(item.offer_percent) / 100)
        item.offer_percent=round(item.offer_percent)

    else:
        item.discounted_price = price
    response = render(request, "commerce/cart/_cart_item.html", {
        "item": item
    })
    response["HX-Trigger"] = json.dumps(data)
    return response


@block_check
@login_required
def decrease_quantity(request, item_id):
    item = get_object_or_404(
        CartItem.objects.select_related("product", "variant", "cart"),
        id=item_id,
        cart__user=request.user
    )

    if item.quantity > 1:
        item.quantity -= 1
        item.save()
        message="Quantity decreased."
    else:
        message = "Minimum quantity reached."
    data = {
        "toast": {"message": message, "type": "warning"},
        "update-cart": True 
    }
    item.offer_percent = get_discount_percentage(item.variant)

    price = Decimal(item.variant.sales_price)
    if item.offer_percent > 0:
        item.discounted_price = price - (price * Decimal(item.offer_percent) / 100)
        item.offer_percent=round(item.offer_percent)
    else:
        item.discounted_price = price
    response = render(request, "commerce/cart/_cart_item.html", {
        "item": item
    })
    response["HX-Trigger"] = json.dumps(data)
    return response

 

@block_check
@login_required
def remove_cart_item(request,item_id):
    
    item = get_object_or_404(
        CartItem.objects.select_related("cart"),
        id=item_id,
        cart__user=request.user
    )  
    cart = item.cart if item else None

    if item:
        item.delete()
    if cart.items.count()==0:
        response=HttpResponse("")
        response["HX-Location"]=reverse("cart_page")
        return response
    response = HttpResponse("")    
    response["HX-Trigger"] = "update-cart"
    return response

@block_check
@login_required
def cart_count(request):
    if not request.user.is_authenticated:
        return HttpResponse("0")  

    cart, created = Cart.objects.get_or_create(user=request.user)
    count = cart.items.count()

    return HttpResponse(count)

@block_check
@login_required
def cart_totals(request):
    if not request.user.is_authenticated:
        return HttpResponse("")

    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related("variant", "product")
    if items.count() == 0:
        return HttpResponse("")

    subtotal =Decimal(0)
    discount = Decimal(0)
    for i in items:
        if not i.variant or i.variant.sales_price is None:
            continue

        price = Decimal(i.variant.sales_price)
        offer_percent = get_discount_percentage(i.variant)

        if offer_percent:
            discounted_price = price - (price * Decimal(offer_percent) / 100)
            discount += (price - discounted_price) * i.quantity
        else:
            discounted_price = price

        subtotal += discounted_price * i.quantity

    if subtotal ==Decimal(0):
        shipping_cost=Decimal("0")
    else:
        shipping_cost = Decimal("0") if subtotal >= 1000 else Decimal("80")
    total = subtotal + shipping_cost

    context = {
        "subtotal": subtotal,
        "shipping_cost": shipping_cost,
        "discount": discount,
        "total": total,
    }

    return render(request, "commerce/cart/_cart_totals.html", context)

@login_required
@never_cache
@cache_control(no_store=True, no_cache=True, must_revalidate=True)
def checkout(request):
    user=request.user
    cart,_=Cart.objects.get_or_create(user=user)
    
    products=cart.items.select_related("variant",'product')
    if not products.exists():
        messages.error(request,"Your cart is empty!")
        return redirect('cart_page')
    
    addresses=user.addresses.filter(is_deleted=False)
    has_address=addresses.exists()
    subtotal = Decimal("0")
    offer_discount = Decimal("0")

    for item in products:
        if item.quantity>item.variant.stock:
            # messages.error(request,f"{item.product.name}-({item.variant.material_type}) is get out of stock!")
            return redirect("cart_page")
        else:
            price = Decimal(item.variant.sales_price)
            offer_percent = get_discount_percentage(item.variant)
            item.offer_percent=offer_percent
            item.discounted_price = price - (price * Decimal(offer_percent) / 100)
            subtotal += item.discounted_price * item.quantity
            offer_discount += (price - item.discounted_price) * item.quantity
    
    coupon_code=request.session.get('applied_coupon')
    coupon_discount=Decimal('0')
    coupon=None
    if coupon_code:
        coupon,coupon_discount,error=validate_and_calculate_coupon(coupon_code,user,subtotal)
        if error:
            messages.error(request, error)
            request.session.pop("applied_coupon", None)
            coupon = None
            coupon_discount = Decimal("0")

    shipping_cost= 0 if subtotal>=1000 else 80
    total = subtotal -coupon_discount + shipping_cost
    now = timezone.now()
    MAX_COD_AMOUNT = Decimal("1000")
    cod_allowed = total <= MAX_COD_AMOUNT

    
    coupons_qs = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=now,
        valid_until__gte=now
    ).annotate(
        total_usage_count=Count('usages'),
        user_usage_count=Count('usages', filter=Q(usages__user=user))
    )

    available_coupons = []
    
    for c in coupons_qs:
        if c.usage_limit is not None and c.total_usage_count >= c.usage_limit:
            continue
        if c.user_usage_count >= c.per_user_limit:
            continue
            
        is_eligible = subtotal >= c.minimum_purchase_amount
        shortage = c.minimum_purchase_amount - subtotal
        
        available_coupons.append({
            'obj': c,
            'is_eligible': is_eligible,
            'reason': None if is_eligible else f"Add ₹{shortage} more"
        })
    request.session["checkout_cart_update_at"]=cart.updated_at.timestamp()
    context={
        "products":products,
        "addresses":addresses,
        "has_address":has_address,

        "subtotal":subtotal,
        "offer_discount":offer_discount,
        "coupon":coupon,
        "coupon_discount":coupon_discount,
        "shipping_cost":shipping_cost,
        "total":total,
        "cod_allowed": cod_allowed,
        "available_coupons": available_coupons,
    }
    return render(request,'commerce/checkout/checkout_page.html',context)

@login_required
def apply_coupon(request):
    if request.method != "POST":
        return redirect("checkout")

    coupon_code = request.POST.get("coupon_code", "").strip()

    if not coupon_code:
        if request.headers.get("HX-Request"):
            return render_checkout_summary(request, error_message="Please enter a coupon code.")
        messages.error(request, "Please enter a coupon code.")
        return redirect("checkout")

    user = request.user
    
    cart = Cart.objects.filter(user=user).first()
    if not cart or not cart.items.exists():
         return render_checkout_summary(request, error_message="Your cart is empty.")

    subtotal = Decimal("0.00")
    for item in cart.items.select_related("variant"):
        price = Decimal(item.variant.sales_price)
        offer_percent = get_discount_percentage(item.variant) or 0
        discounted_price = price - (price * Decimal(offer_percent) / 100)
        subtotal += discounted_price * item.quantity

    coupon, discount, error = validate_and_calculate_coupon(coupon_code, user, subtotal)

    if error:
        request.session.pop("applied_coupon", None)
        if request.headers.get("HX-Request"):
            return render_checkout_summary(request, error_message=error)
            
        messages.error(request, error)
        return redirect("checkout")

    request.session["applied_coupon"] = coupon.code

    if request.headers.get("HX-Request"):
        return render_checkout_summary(request, success_message=f"Coupon '{coupon.code}' applied!")

    messages.success(request, f"Coupon '{coupon.code}' applied!")
    return redirect("checkout")


@login_required
def remove_coupon(request):
    request.session.pop("applied_coupon", None)

    if request.headers.get("HX-Request"):
        return render_checkout_summary(request, success_message="Coupon removed.")

    messages.info(request, "Coupon removed.")
    return redirect("checkout")

@login_required
def place_order(request):
    if request.method != "POST":
        return redirect("checkout")

    if not request.POST.get("address"):
        messages.error(request, "Please select an address.")
        return redirect("checkout")

    user = request.user
    cart, _ = Cart.objects.get_or_create(user=user)

    last_checkout_time = request.session.get("checkout_cart_update_at")
    if last_checkout_time and float(last_checkout_time) != float(cart.updated_at.timestamp()):
        messages.error(request, "Your cart was updated. Please review checkout again.")
        request.session.pop("applied_coupon", None)
        return redirect("checkout")

    with transaction.atomic():
        items = (
            cart.items
            .select_related("variant", "product")
            .select_for_update()
        )

        if not items.exists():
            messages.error(request, "Your cart is empty!")
            return redirect("cart_page")

        address = get_object_or_404(
            UserAddress,
            id=request.POST.get("address"),
            user=user
        )

        payment_method = request.POST.get("payment_method")

        #  STOCK VALIDATION 
        for item in items:
            if item.variant.stock == 0:
                request.session.pop("applied_coupon", None)
                return redirect("cart_page")
            elif item.quantity > item.variant.stock:
                request.session.pop("applied_coupon", None)
                messages.error(
                    request,
                    f"Only {item.variant.stock} left for {item.variant.material_type}."
                )
                return redirect("cart_page")

        # PRICE CALCULATION 
        subtotal = Decimal("0")
        offer_discount = Decimal("0")

        for item in items:
            unit_price = Decimal(item.variant.sales_price)
            offer_percent = get_discount_percentage(item.variant)
            discounted_price = unit_price - (unit_price * Decimal(offer_percent) / 100)

            subtotal += discounted_price * item.quantity
            offer_discount += (unit_price - discounted_price) * item.quantity

        coupon = None
        coupon_discount = Decimal("0")

        coupon_code = request.session.get("applied_coupon")
        if coupon_code:
            coupon, coupon_discount, error = validate_and_calculate_coupon(
                coupon_code, user, subtotal
            )
            if error:
                coupon = None
                coupon_discount = Decimal("0")

        delivery_charge = 0 if subtotal >= 1000 else 80
        total = subtotal - coupon_discount + delivery_charge

        if payment_method == "wallet":
            wallet=Wallet.objects.filter(user=user).first()
            if not wallet or wallet.balance<total:  
                messages.error(request, "Insufficient wallet balance.")
                return redirect("checkout") 
        if payment_method == "cod" and total > Decimal("1000"):
            messages.error(
                request,
                "Cash on Delivery is not available for orders above ₹1000."
            )
            return redirect("checkout")
        
        order = Orders.objects.create(
            user=user,
            address=address,
            total_price_before_discount=subtotal + offer_discount,
            offer_discount=offer_discount,
            coupon=coupon,
            coupon_discount=coupon_discount,
            total_price=total,
            payment_method=payment_method,
            delivery_charge=delivery_charge,
            payment_status="pending"
        )

        for item in items:
            unit_price = Decimal(item.variant.sales_price)
            offer_percent = get_discount_percentage(item.variant)
            final_price = unit_price - (unit_price * Decimal(offer_percent) / 100)

            OrderItem.objects.create(
                order=order,
                product=item.variant,
                quantity=item.quantity,
                unit_price=unit_price,
                price=final_price * item.quantity,
                offer_percent=offer_percent
            )
        
        if coupon:
            usage_count = coupon.usages.filter(user=user).count()
            total_usages = coupon.usages.count()
            
            if usage_count >= coupon.per_user_limit:
                raise ValueError("Per user limit exceeded")
            if total_usages >= coupon.usage_limit:
                raise ValueError("Total usage limit exceeded")
            CouponUsage.objects.create(
            coupon=coupon,
            user=user,
            order=order
        )

        # WALLET
        if payment_method == "wallet":
            try:
                pay_using_wallet(user=user, order=order, amount=total)
            except InsufficientWalletBalance:
                messages.error(request, "Insufficient wallet balance.")
                return redirect("checkout") 

            # reduce stock + clear cart
            for item in items:
                item.variant.stock -= item.quantity
                item.variant.save(update_fields=["stock"])

            items.delete()
            request.session.pop("checkout_cart_update_at", None)
            request.session.pop("applied_coupon", None)

            messages.success(request, "Your order was placed successfully!")
            return redirect("order_success", order_id=order.order_id)

        if payment_method == "cod":
            for item in items:
                item.variant.stock -= item.quantity
                item.variant.save(update_fields=["stock"])

            items.delete()
            order.payment_status = "pending"
            order.save(update_fields=["payment_status"])

            request.session.pop("checkout_cart_update_at", None)
            request.session.pop("applied_coupon", None)

            messages.success(request, "Your order was placed successfully!")
            return redirect("order_success", order_id=order.order_id)

        if payment_method == "razorpay":
            return redirect("razorpay_start", order_id=order.order_id)

    return redirect("checkout")

@login_required
@never_cache
@cache_control(no_store=True, no_cache=True, must_revalidate=True)
def start_razorpay_payment(request, order_id):
    order = get_object_or_404(
        Orders, order_id=order_id, user=request.user
    )

    if order.payment_status == "paid":
        return redirect("order_success", order_id=order.order_id)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    razorpay_order = client.order.create({
        "amount": int(order.total_price * 100),
        "currency": "INR",
        "payment_capture": 1
    })

    order.razorpay_order_id = razorpay_order["id"]
    order.payment_status = "pending"
    order.save(update_fields=["razorpay_order_id"])

    return render(request, "commerce/payments/razorpay_checkout.html", {
        "order": order,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"],
    })

@csrf_exempt
@never_cache    
def razorpay_success(request):
    data = json.loads(request.body)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"],
        })

        with transaction.atomic():
            order = Orders.objects.select_for_update().get(
                Q(payment_status="pending") | Q(payment_status="failed"),
                razorpay_order_id=data["razorpay_order_id"],
            )            
            if not request.user.is_authenticated or order.user_id != request.user.id:
                raise PermissionDenied

            payment = client.payment.fetch(data["razorpay_payment_id"])
            if payment["status"] == "authorized":
                client.payment.capture(
                    data["razorpay_payment_id"],
                    int(order.total_price * 100)
                )

            for item in order.items.select_related("product"):
                if item.quantity > item.product.stock:
                    raise ValueError("Stock mismatch during Razorpay success")

                item.product.stock -= item.quantity
                item.product.save(update_fields=["stock"])

            CartItem.objects.filter(cart__user=order.user).delete()

            order.payment_status = "paid"
            order.payment_method = "razorpay"
            order.razorpay_payment_id = data["razorpay_payment_id"]
            order.razorpay_signature = data["razorpay_signature"]
            order.save(update_fields=[
                "payment_status",
                "payment_method",
                "razorpay_payment_id",
                "razorpay_signature"
            ])
        request.session.pop("applied_coupon", None)
        request.session.pop("checkout_cart_update_at", None)
        return JsonResponse({"success": True})

    except Orders.DoesNotExist:
        return JsonResponse({"success": True})

    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({"success": False}, status=400)

    except Exception as e:
        logger.exception("Razorpay success processing failed")
        return JsonResponse({"success": False}, status=500)

@csrf_exempt
@never_cache
def razorpay_failed(request):
    logger.error("razorpay_failed view HIT")
    data = json.loads(request.body)

    try:
        order = Orders.objects.get(
            order_id=data["order_id"],
            payment_status="pending"
        )
        order.payment_status = "failed"
        order.save(update_fields=["payment_status"])
        CartItem.objects.filter(cart__user=order.user).delete()
        request.session.pop("applied_coupon", None)

    except Orders.DoesNotExist:
        pass
    
    return JsonResponse({"success": True})


@login_required
@never_cache
def payment_failed(request,order_id):
    order = get_object_or_404(
        Orders,
        order_id=order_id,
        user=request.user,
        payment_status__in=["failed",'pending']
    )
    return render(request, "commerce/payments/payment_failed.html", {"order": order})


@login_required
@never_cache
def order_success(request,order_id):
    order=get_object_or_404(
        Orders.objects.select_related("address").prefetch_related("items__product"),
        order_id=order_id,
        user=request.user
    )
    request.session.pop("applied_coupon", None)
    return render(request,"commerce/order/order_success.html",{"order":order})

@login_required
def my_orders(request):
    orders=Orders.objects.filter(user=request.user).order_by("-created_at")
    paginator = Paginator(orders, 5)  
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request,"commerce/order/my_orders.html",{"orders":orders,"page_obj": page_obj})


@login_required
def user_order_detail(request, order_id):
    order = get_object_or_404(Orders, order_id=order_id, user=request.user)
    items = order.items.select_related("product", "product__product")
    return render(request, "commerce/order/order_details.html", {
        "order": order,
        "items": items,
    })


@login_required
def download_invoice(request, order_id):
    styles = get_invoice_styles()

    order = get_object_or_404(
        Orders.objects.prefetch_related("items__product"),
        order_id=order_id,
        user=request.user,
        payment_status__in =["paid","partially_refunded","refunded"]
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Invoice_{order.order_id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    # Title 
    elements.append(Paragraph("FURNICRAFT INVOICE", styles["title"]))
    elements.append(Spacer(1, 10))

    # Order Meta 
    meta_table = Table(
        [
            ["Order ID:", order.order_id, "Date:", order.created_at.strftime("%d %b %Y")]
        ],
        colWidths=[70, 180, 50, 120]
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 15))

    #  Billing Address 
    addr = order.address
    elements.append(Paragraph("Bill To", styles["bold"]))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(addr.name, styles["value"]))
    elements.append(Paragraph(f"{addr.house}, {addr.street}", styles["value"]))
    elements.append(Paragraph(f"{addr.district}, {addr.state} - {addr.pincode}", styles["value"]))
    elements.append(Spacer(1, 20))

    # Items Table 
    table_data = [["Product", "Qty", "Unit Price", "Final Price"]]

    for item in order.items.all():
        table_data.append([
            f"{item.product.product.name} ({item.product.material_type})",
            item.quantity,
            f"₹{item.unit_price}",
            f"₹{item.price}",
        ])

    table = Table(table_data, colWidths=[230, 50, 90, 90])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    paid_subtotal = sum(item.unit_price * item.quantity for item in order.items.all())
    paid_total = (paid_subtotal - order.offer_discount - order.coupon_discount + order.delivery_charge)

    #  Summary 
    summary_data = [
        ["Subtotal", f"₹{order.total_price_before_discount}"],
    ]

    if order.offer_discount > 0:
        summary_data.append(["Offer Discount", f"- ₹{order.offer_discount}"])

    if order.coupon:
        summary_data.append([f"Coupon ({order.coupon.code})", f"- ₹{order.coupon_discount}"])

    summary_data.append(["Shipping", f"₹{order.delivery_charge}"])
    summary_data.append(["", ""])
    summary_data.append(["TOTAL PAID", f"₹{paid_total}"])

    summary_table = Table(summary_data, colWidths=[300, 160], hAlign="RIGHT")
    summary_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("LINEABOVE", (0, -1), (-1, -1), 1.2, colors.black),
        ("TOPPADDING", (0, -1), (-1, -1), 10),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 25))

    elements.append(
        Paragraph(
            "This is a system-generated invoice and does not require a signature.",
            styles["label"]
        )
    )

    doc.build(elements)
    return response


@login_required
def my_orders_page(request):
    orders_qs=Orders.objects.filter(user=request.user).order_by("-created_at")
    paginator = Paginator(orders_qs, 4)  
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request,"commerce/order/my_orders_page.html",
                  {"orders":page_obj,
                   "page_obj": page_obj})

@login_required
def cancel_order_item(request,item_id):
    item=get_object_or_404(OrderItem.objects.select_related("order","product"),
                           id=item_id,
                           order__user=request.user)
    if item.status!='order_received':
        messages.error(request,"This item cannot be cancelled!")
        return redirect("user_order_detail",item.order.order_id)
    with transaction.atomic():
        order=item.order
        if item.status == 'cancelled':
            messages.error(request, "Item already cancelled.")
            return redirect("user_order_detail", order.order_id)
        item.status="cancelled"
        item.save(update_fields=["status"])

        item.product.stock+=item.quantity
        item.product.save(update_fields=['stock'])

        if order.payment_status in ['paid','partially_refunded']:
            wallet,_=Wallet.objects.get_or_create(user=request.user)

            coupon_share = calculate_item_coupon_share(order, item)

            refund_amount=item.price - coupon_share

            wallet.balance+=refund_amount
            wallet.save(update_fields=["balance"])

            WalletTransaction.objects.create(
                wallet=wallet,
                order=order,
                amount=refund_amount,
                transaction_type='credit',
                source='order_cancel'
            )
            messages.success(
            request,f"Item cancelled. ₹{refund_amount} refunded to your wallet."
        )
        else:
            messages.success(
            request,f"Item cancelled.")

        remaining_items=order.items.exclude(status="cancelled")
        new_total=sum(i.price for i in remaining_items)
        if order.payment_status in ['paid', 'partially_refunded']:
            if new_total==0:
                order.payment_status='refunded'
            else:
                order.payment_status='partially_refunded'
            order.total_price=new_total+order.delivery_charge
            order.save(update_fields=['total_price','payment_status'])
        else:
            order.payment_status='failed'
            order.save(update_fields=['payment_status'])
    return redirect("user_order_detail",order.order_id)

@login_required
def request_return(request, item_id):
    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order__user=request.user,
        status="delivered"
    )

    # Prevent duplicate returns
    if OrderReturn.objects.filter(item=item).exists():
        messages.error(request, "Return already requested for this item.")
        return redirect("user_order_detail", item.order.order_id)

    if request.method == "POST":
        reason = request.POST.get("return_reason")
        return_type = request.POST.get("return_status")
        image = request.FILES.get("image")

        if not reason:
            messages.error(request, "Please select a return reason.")
            return redirect(request.path)

        OrderReturn.objects.create(
            user=request.user,
            item=item,
            return_reason=reason,
            return_status=return_type,
            approval_status="pending",
            image=image
        )

        messages.success(request, "Return request submitted.")
        return redirect("user_order_detail", item.order.order_id)

    return render(
        request,
        "commerce/order/return_request.html",
        {"item": item}
    )


@login_required
def my_wallet(request):
    wallet,_=Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.select_related("order").order_by("-created_at")

    paginator=Paginator(transactions,3)
    page_obj=paginator.get_page(request.GET.get('page'))

    context = {
            "wallet": wallet,
            "page_obj": page_obj,
        }
    if request.headers.get("HX-Request"):
        return render(request, "commerce/wallet/wallet.html", context)
    return render(request,"commerce/wallet/my_wallet.html",context)


def add_checkout_address(request):
    return render(request,"commerce/checkout/add_checkout_address.html")
