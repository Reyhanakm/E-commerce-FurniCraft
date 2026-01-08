from decimal import Decimal
from django.utils import timezone
from product.models import Coupon, CouponUsage

def validate_and_calculate_coupon(coupon_code, user, subtotal):
    try:
        coupon = Coupon.objects.get(
            code__iexact=coupon_code,
            is_active=True,
            is_deleted=False
        )
    except Coupon.DoesNotExist:
        return None, Decimal("0"), "Invalid coupon code."

    now = timezone.now()

    if now < coupon.valid_from:
        return None, Decimal("0"), "This coupon is not active yet."

    if now > coupon.valid_until:
        return None, Decimal("0"), "This coupon has expired."

    if subtotal < coupon.minimum_purchase_amount:
        return None, Decimal("0"), f"Minimum order value ₹{coupon.minimum_purchase_amount} required."
    
    if coupon.usage_limit is not None:
        if coupon.usages.count() >= coupon.usage_limit:
            return None, Decimal("0"), "Coupon usage limit reached."

    user_usage_count = CouponUsage.objects.filter(
        coupon=coupon,
        user=user
    ).count()

    if user_usage_count >= coupon.per_user_limit:
        return None, Decimal("0"), "You have already used this coupon."

    # calculate discount
    if coupon.discount_type == "percentage":
        discount = subtotal * Decimal(coupon.discount_value) / 100
    else:
        discount = Decimal(coupon.discount_value)

    # apply max discount cap
    if coupon.maximum_discount_limit is not None:
        discount = min(discount, coupon.maximum_discount_limit)

    return coupon, discount, None


def calculate_item_coupon_share(order, item):
    """
    Returns coupon discount portion applicable to a single order item
    """
    if not order.coupon or order.coupon_discount <= 0:
        return Decimal("0.00")

    # Total order value AFTER offers, BEFORE coupon
    order_items_total = sum(i.price * i.quantity for i in order.items.all())

    if order_items_total == 0:
        return Decimal("0.00")
    
    item_totals =item.price * item.quantity

    # Proportional coupon share
    item_coupon_share = (
        item_totals / order_items_total
    ) * order.coupon_discount

    return item_coupon_share.quantize(Decimal("0.01"))
