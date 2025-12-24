from django.db import transaction
from decimal import Decimal

from commerce.models import OrderReturn, OrderItem, Orders,Wallet, WalletTransaction
from commerce.utils.coupons import calculate_item_coupon_share


# @transaction.atomic
# def approve_return_service(return_request: OrderReturn):
#     """
#     Approves a return request and processes wallet refund (coupon-aware)
#     """
#     if return_request.approval_status != "pending":
#         raise ValueError("Return already processed")


#     item = return_request.item
#     order = item.order
#     user = return_request.user

#     # Mark return as approved
#     return_request.approval_status = "approved"
#     return_request.save(update_fields=["approval_status"])

#     #  Mark item as returned
#     item.status = "returned"
#     item.save(update_fields=["status"])

#     #  Calculate refund (IMPORTANT)
#     coupon_share = calculate_item_coupon_share(order, item)
#     refund_amount = item.price - coupon_share

#     if refund_amount < Decimal("0.00"):
#         refund_amount = Decimal("0.00")

#     #  Credit wallet
#     wallet, _ = Wallet.objects.get_or_create(user=user)
#     wallet.balance += refund_amount
#     wallet.save(update_fields=["balance"])
#     #  after wallet credit
#     return_request.approval_status = "refunded"
#     return_request.save(update_fields=["approval_status"])

#     WalletTransaction.objects.create(
#         wallet=wallet,
#         order=order,
#         amount=refund_amount,
#         transaction_type="credit",
#         source="order_return",
#         is_paid=True
#     )

#     #  Update order payment status
#     refunded_items = order.items.filter(
#         status__in=["cancelled", "returned"]
#     ).count()

#     total_items = order.items.count()

#     if refunded_items == total_items:
#         order.is_paid = "refunded"
#     else:
#         order.is_paid = "partially_refunded"

#     order.save(update_fields=["is_paid"])

#     return refund_amount
@transaction.atomic
def approve_return_service(return_request: OrderReturn):

    if return_request.approval_status != "pending":
        raise ValueError("Return already processed")

    item = return_request.item
    order = item.order
    user = return_request.user

    # Mark approved
    return_request.approval_status = "approved"
    return_request.save(update_fields=["approval_status"])

    # Mark item returned
    item.status = "returned"
    item.save(update_fields=["status"])

    # Calculate refund
    coupon_share = calculate_item_coupon_share(order, item) or Decimal("0.00")
    refund_amount = max(item.price - coupon_share, Decimal("0.00"))

    # Credit wallet
    wallet, _ = Wallet.objects.get_or_create(user=user)
    wallet.balance += refund_amount
    wallet.save(update_fields=["balance"])

    WalletTransaction.objects.create(
        wallet=wallet,
        order=order,
        amount=refund_amount,
        transaction_type="credit",
        source="order_return"
    )

    # Update return as refunded
    return_request.approval_status = "refunded"
    return_request.save(update_fields=["approval_status"])

    # Update order payment status
    refunded_items = order.items.filter(
        status__in=["cancelled", "returned"]
    ).count()

    order.payment_status = (
        "refunded" if refunded_items == order.items.count()
        else "partially_refunded"
    )
    order.save(update_fields=["payment_status"])

    return refund_amount
