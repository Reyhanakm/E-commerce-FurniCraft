from django.db.models import Q

def sync_order_payment_status_from_items(order):
    items = order.items.all()

    if not items.exists():
        return

    all_cancelled_or_returned = all(
        item.status in ["cancelled", "returned"]
        for item in items
    )

    some_cancelled_or_returned = any(
        item.status in ["cancelled", "returned"]
        for item in items
    )

    if all_cancelled_or_returned:
        order.payment_status = "refunded"

    elif some_cancelled_or_returned:
        order.payment_status = "partially_refunded"

    else:
        return  

    order.save(update_fields=["payment_status"])
