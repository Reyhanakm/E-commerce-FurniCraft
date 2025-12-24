from decimal import Decimal
from django.shortcuts import render
from commerce.utils.offers import get_discount_percentage
from commerce.utils.coupons import validate_and_calculate_coupon
from commerce.models import Cart

def render_checkout_summary(request):
    user = request.user
    cart = Cart.objects.get(user=user)
    items = cart.items.select_related("variant", "product")

    subtotal = Decimal("0")
    offer_discount = Decimal("0")

    for item in items:
        price = Decimal(item.variant.sales_price)
        offer_percent = get_discount_percentage(item.variant)
        discounted_price = price - (price * Decimal(offer_percent) / 100)

        subtotal += discounted_price * item.quantity
        offer_discount += (price - discounted_price) * item.quantity

    coupon = None
    coupon_discount = Decimal("0")
    coupon_code = request.session.get("applied_coupon")

    if coupon_code:
        coupon, coupon_discount, _ = validate_and_calculate_coupon(
            coupon_code, user, subtotal
        )

    shipping_cost = Decimal("0") if subtotal >= 1000 else Decimal("80")
    total = subtotal - coupon_discount + shipping_cost

    return render(
        request,
        "commerce/checkout/_coupon_totals.html",
        {
            "coupon": coupon,
            "coupon_discount": coupon_discount,
            "offer_discount": offer_discount,
            "subtotal": subtotal,
            "shipping_cost": shipping_cost,
            "total": total,
        }
    )
