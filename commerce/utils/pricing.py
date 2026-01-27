from decimal import ROUND_UP, Decimal
from .offers import get_best_offer

def _calculate_discount(base_price, offer):
    if offer.discount_type == 'percentage':
        discount = (base_price * offer.discount_percent) / Decimal(100)
        if offer.max_discount_amount:
            discount = min(discount, offer.max_discount_amount)
    else:
        discount = offer.discount_percent

    return max(Decimal(0), discount)


def get_pricing_context(variant):
    base_price = variant.sales_price
    best_price = base_price
    applied_discount = Decimal(0)

    offer = get_best_offer(variant)

    if offer:
        discount = _calculate_discount(base_price, offer)
        best_price = base_price - discount
        applied_discount = discount

    offer_percent = (
        (applied_discount / base_price) * 100
        if base_price > 0 and applied_discount > 0
        else Decimal(0)
    )
    display_offer_percent = (
    max(Decimal(1), offer_percent.quantize(0, rounding=ROUND_UP))
    if offer_percent > 0
    else Decimal(0)
)

    return {
        "mrp": variant.regular_price,
        "base_price": base_price,
        "current_price": max(Decimal(0), best_price),
        "offer_percent": int(display_offer_percent),
        "is_offer_applied": bool(applied_discount),
        "applied_offer": offer,
    }


def attach_best_pricing_to_products(products):
    
    for product in products:
        best_pricing = None
        best_price = None

        for variant in product.variants.all():
            pricing = get_pricing_context(variant)

            if best_price is None or pricing["current_price"] < best_price:
                best_price = pricing["current_price"]
                best_pricing = pricing

        product.pricing = best_pricing
        product.display_price = best_price


