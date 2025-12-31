from django.db import transaction
from decimal import Decimal

from commerce.models import OrderReturn, OrderItem, Orders,Wallet, WalletTransaction
from commerce.utils.coupons import calculate_item_coupon_share

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
@transaction.atomic
def refund_order_to_wallet(order, amount):
    if amount <= 0:
        return

    wallet, _ = Wallet.objects.select_for_update().get_or_create(
        user=order.user
    )

    if WalletTransaction.objects.filter(
        wallet=wallet,
        order=order,
        source="order_cancel"
    ).exists():
        return

    wallet.balance += Decimal(amount)
    wallet.save(update_fields=["balance"])

    WalletTransaction.objects.create(
        wallet=wallet,
        order=order,
        amount=amount,
        transaction_type="credit",
        source="order_cancel"
    )


@transaction.atomic
def refund_return_item_to_wallet(return_obj):
    item = return_obj.item
    order = item.order

    if order.payment_status != "paid":
        return

    wallet, _ = Wallet.objects.select_for_update().get_or_create(
        user=order.user
    )

    if WalletTransaction.objects.filter(
        wallet=wallet,
        order=order,
        source="order_return",
        amount=item.price
    ).exists():
        return

    wallet.balance += item.price
    wallet.save(update_fields=["balance"])

    WalletTransaction.objects.create(
        wallet=wallet,
        order=order,
        amount=item.price,
        transaction_type="credit",
        source="order_return"
    )