from commerce.models import OrderItem

def is_first_successful_order(user):
    return not OrderItem.objects.filter(
        order__user=user,
        status='delivered'
    ).exists()