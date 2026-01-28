from django.utils import timezone
from decimal import Decimal

def get_active_product_offer(variant):
    now = timezone.now()
    offers = variant.product.product_offers.filter(
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    )
    
    best_offer = None
    max_savings = Decimal('0.00')

    for offer in offers:
        savings = calculate_effective_discount(offer, variant.sales_price)
        if savings >= max_savings:
            max_savings = savings
            best_offer = offer
            
    return best_offer


def get_active_category_offer(variant):
    now = timezone.now()
    offers = variant.product.category.category_offers.filter(
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    )
    
    best_offer = None
    max_savings = Decimal('0.00')

    for offer in offers:
        savings = calculate_effective_discount(offer, variant.sales_price)
        if savings >= max_savings:
            max_savings = savings
            best_offer = offer
            
    return best_offer


def calculate_effective_discount(offer, price):
    if not offer:
        return Decimal('0.00')
        
    discount_amount = (price * offer.discount_percent) / 100
    
    if offer.max_discount_amount and discount_amount > offer.max_discount_amount:
        discount_amount = offer.max_discount_amount
        
    return discount_amount


def get_best_offer(variant):
    product_offer = get_active_product_offer(variant)
    category_offer = get_active_category_offer(variant)

    p_savings = calculate_effective_discount(product_offer, variant.sales_price)
    c_savings = calculate_effective_discount(category_offer, variant.sales_price)

    if p_savings >= c_savings and p_savings > 0:
        return product_offer
    elif c_savings > p_savings:
        return category_offer
    
    return None


def get_discount_percentage(variant):
    offer = get_best_offer(variant)
    if not offer:
        return 0

    effective_discount = calculate_effective_discount(offer, variant.sales_price)

    if effective_discount <= 0:
        return 0

    percent = (effective_discount / variant.sales_price) * 100
    return int(percent.quantize(Decimal("1")))
