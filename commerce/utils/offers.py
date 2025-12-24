from django.utils import timezone

def get_active_product_offer(variant):
    now = timezone.now()
    return (
        variant.product.product_offers
        .filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )
        .order_by("-discount_value")
        .first()
    )


def get_active_category_offer(variant):
    now = timezone.now()
    return (
        variant.product.category.category_offers
        .filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )
        .order_by("-discount_value")
        .first()
    )


def get_best_offer(variant):
    product_offer = get_active_product_offer(variant)
    category_offer = get_active_category_offer(variant)

    if product_offer and category_offer:
        return (
            product_offer
            if product_offer.discount_value >= category_offer.discount_value
            else category_offer
        )

    return product_offer or category_offer


def get_discount_percentage(variant):
    offer = get_best_offer(variant)
    return offer.discount_value if offer else 0
