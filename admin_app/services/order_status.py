from django.core.exceptions import ValidationError
from commerce.utils.referral import process_referral_after_first_order
from commerce.utils.orders import is_first_successful_order
from .order_payment import sync_order_payment_status_from_items

ORDER_PAYMENT_TRANSITIONS = {
    "pending": ["paid", "failed"],
    "paid": ["partially_refunded", "refunded"],
    "partially_refunded": ["refunded"],
    "refunded": [],
    "failed": [],
}

ITEM_STATUS_TRANSITIONS = {
    "order_received": ["shipped", "cancelled"],
    "shipped": ["in_transit"],
    "in_transit": ["delivered"],
    "delivered": ["returned"],
    "cancelled": [],
    "returned": [],
}
def update_order_payment_status(order, new_status):
    #Lock after refund
    if order.payment_status == "refunded":
        raise ValidationError(
            "Payment status cannot be changed after refund."
        )

    if order.payment_status == "partially_refunded":
        raise ValidationError(
            "Payment status is system-controlled for partially refunded orders."
        )

    #  Item-level validation 
    items = order.items.all()

    if not items.exists():
        raise ValidationError("Order has no items.")

    all_cancelled_or_returned = all(
        item.status in ["cancelled", "returned"]
        for item in items
    )

    some_cancelled_or_returned = any(
        item.status in ["cancelled", "returned"]
        for item in items
    )

    if all_cancelled_or_returned:
        raise ValidationError(
            "All items are cancelled or returned. Order must be refunded."
        )

    if some_cancelled_or_returned:
        raise ValidationError(
            "Payment status is automatically managed for partially cancelled/returned orders."
        )

    #State machine validation
    allowed = ORDER_PAYMENT_TRANSITIONS.get(order.payment_status, [])

    if new_status not in allowed:
        raise ValidationError(
            f"Cannot change order payment status from {order.payment_status} to {new_status}"
        )

    #  Apply update 
    order.payment_status = new_status
    order.save(update_fields=["payment_status"])


def update_order_item_status(item, new_status):
    allowed = ITEM_STATUS_TRANSITIONS.get(item.status, [])

    if new_status not in allowed:
        raise ValidationError(
            f"Cannot change item status from {item.status} to {new_status}"
        )
    old_status = item.status
    item.status = new_status
    item.save(update_fields=["status"])
    if (
        old_status != "delivered"
        and new_status == "delivered"
        and is_first_successful_order(item.order.user)
    ):
        process_referral_after_first_order(item.order.user)
        
    if new_status in ["cancelled", "returned"]:
        sync_order_payment_status_from_items(item.order)
