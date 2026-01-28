from decimal import Decimal
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.shortcuts import render
from commerce.utils.offers import get_discount_percentage
from commerce.utils.coupons import validate_and_calculate_coupon
from commerce.models import Cart
from commerce.utils.trigger import attach_trigger
from product.models import Coupon


def render_checkout_summary(request, error_message=None, success_message=None):
    """
    Calculates totals, fetches available coupons, and renders the coupon block HTML.
    """
    user = request.user
    
    cart = Cart.objects.filter(user=user).first()
    
    if not cart:
        return HttpResponse('<div id="coupon-section" class="p-4 text-red-500">Cart is empty.</div>')

    items = cart.items.select_related("variant", "product")
    subtotal = Decimal("0")
    offer_discount = Decimal("0")

    for item in items:
        price = Decimal(item.variant.sales_price)
        offer_percent = get_discount_percentage(item.variant) or 0
        discounted_price = price - (price * Decimal(offer_percent) / 100)

        subtotal += discounted_price * item.quantity
        offer_discount += (price - discounted_price) * item.quantity

    coupon_code = request.session.get("applied_coupon")
    coupon = None
    coupon_discount = Decimal("0")

    if coupon_code:
        coupon, coupon_discount, err = validate_and_calculate_coupon(coupon_code, user, subtotal)
        
        # If coupon is invalid (e.g. cart total dropped), remove it
        if err:
            request.session.pop("applied_coupon", None)
            coupon = None
            coupon_discount = Decimal("0")
            # Only set error if one wasn't passed in already
            if not error_message: 
                error_message = err

    shipping_cost = Decimal("0") if subtotal >= 1000 else Decimal("80")
    total = subtotal - coupon_discount + shipping_cost
    cod_allowed= total<=1000


    now = timezone.now()
    
    coupons_qs = Coupon.objects.filter(
        is_active=True,
        is_deleted=False,
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

    context = {
        "coupon": coupon,
        "coupon_discount": coupon_discount,
        "offer_discount": offer_discount,
        "subtotal": subtotal,
        "shipping_cost": shipping_cost,
        "total": total,
        "cod_allowed":cod_allowed,
        "available_coupons": available_coupons,
    }

    response = render(request, "commerce/checkout/_coupon_response.html", context)

    if error_message:
        return attach_trigger(response, error_message, type="error")
    if success_message:
        return attach_trigger(response, success_message, type="success")

    return response

# def render_checkout_summary(request):
#     user = request.user
#     cart = Cart.objects.get(user=user)
#     items = cart.items.select_related("variant", "product")

#     subtotal = Decimal("0")
#     offer_discount = Decimal("0")

#     for item in items:
#         price = Decimal(item.variant.sales_price)
#         offer_percent = get_discount_percentage(item.variant) or 0
#         discounted_price = price - (price * Decimal(offer_percent) / 100)

#         subtotal += discounted_price * item.quantity
#         offer_discount += (price - discounted_price) * item.quantity

#     coupon = None
#     coupon_discount = Decimal("0")
#     coupon_code = request.session.get("applied_coupon")

#     if coupon_code:
#         coupon, coupon_discount,err = validate_and_calculate_coupon(
#             coupon_code, user, subtotal
#         )

#     shipping_cost = Decimal("0") if subtotal >= 1000 else Decimal("80")
#     total = subtotal - coupon_discount + shipping_cost

#     return render(
#         request,
#         "commerce/checkout/_coupon_totals.html",
#         {
#             "coupon": coupon,
#             "coupon_discount": coupon_discount,
#             "offer_discount": offer_discount,
#             "subtotal": subtotal,
#             "shipping_cost": shipping_cost,
#             "total": total,
#         }
#     )
