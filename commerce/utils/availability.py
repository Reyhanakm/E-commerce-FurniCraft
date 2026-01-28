from decimal import Decimal

def check_item_availability(item):
    variant = item.variant
    product = variant.product
    category = product.category

    if category.is_deleted:
        return False, f"Category '{category.name}' is unavailable."

    if product.is_deleted:
        return False, f"Product '{product.name}' is unavailable."

    if variant.is_deleted:
        return False, f"Selected material is unavailable for '{product.name}'."

    # if item.quantity > variant.stock:
    #     return False, f"Only {variant.stock} items left for '{product.name}'."

    return True, None
