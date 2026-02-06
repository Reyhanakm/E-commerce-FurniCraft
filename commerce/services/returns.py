from django.db import transaction
from decimal import Decimal
from django.db.models import F,Sum

from commerce.models import OrderReturn, OrderItem, Orders,Wallet, WalletTransaction
from commerce.utils.coupons import calculate_item_coupon_share

@transaction.atomic
def process_refund_to_wallet(order, amount, source):
  
    amount = Decimal(amount)
    if amount <= 0:
        return Decimal("0.00")

    max_refundable = order.original_total 
    already_refunded = order.refunded_amount
    
    refundable_now = max_refundable - already_refunded
    
    if refundable_now <= 0:
        return Decimal("0.00")
    
    if amount > refundable_now:
        amount = refundable_now
    
    wallet, _ = Wallet.objects.select_for_update().get_or_create(user=order.user)

    if WalletTransaction.objects.filter(wallet=wallet, order=order, source=source).exists():
        return Decimal("0.00")

    order.refunded_amount += amount
    order.save(update_fields=['refunded_amount'])

    wallet.balance += amount
    wallet.save(update_fields=["balance"])

    WalletTransaction.objects.create(
        wallet=wallet,
        order=order,
        amount=amount,
        transaction_type="credit",
        source=source
    )

    return amount

@transaction.atomic
def approve_return_service(return_request: OrderReturn):
    if return_request.approval_status != "pending":
        raise ValueError("Return already processed")

    item = return_request.item
    order = item.order

    return_request.approval_status = "approved"
    item.status = "returned"
    
    item.product.stock = F('stock') + item.quantity
    item.product.save(update_fields=["stock"])
    potential_refund =Decimal('0.00')
    if order.payment_status in ["paid", "partially_refunded"]:
        coupon_share = calculate_item_coupon_share(order, item)

        potential_refund = max(item.price - coupon_share, Decimal("0.00"))
        
        # pass a unique source including the item ID
        process_refund_to_wallet(
            order=order, 
            amount=potential_refund, 
            source=f"order return: (product:{item.id})"
        )

    # Finalize statuses
    return_request.approval_status = "refunded"
    return_request.save(update_fields=["approval_status"])
    item.save(update_fields=["status"])

    # Update Order Level Status
    all_returned_or_cancelled = not order.items.exclude(status__in=["cancelled", "returned","failed"]).exists()
    order.payment_status = "refunded" if all_returned_or_cancelled else "partially_refunded"
    order.save(update_fields=["payment_status"])

    return potential_refund


# @transaction.atomic
# def approve_return_service(return_request: OrderReturn):

#     if return_request.approval_status != "pending":
#         raise ValueError("Return already processed")

#     item = return_request.item
#     order = item.order
#     user = return_request.user

#     # Mark approved
#     return_request.approval_status = "approved"
#     return_request.save(update_fields=["approval_status"])

#     # Mark item returned
#     item.status = "returned"
#     item.save(update_fields=["status"])

#     variant = (type(item.product).objects.select_for_update().get(pk=item.product.pk))
#     variant.stock+=F("stock") + item.quantity
#     variant.save(update_fields=["stock"])

#     # Calculate refund
#     coupon_share = calculate_item_coupon_share(order, item) or Decimal("0.00")
#     refund_amount = max(item.price - coupon_share, Decimal("0.00"))

#     # Credit wallet
#     wallet, _ = Wallet.objects.get_or_create(user=user)
#     wallet.balance += refund_amount
#     wallet.save(update_fields=["balance"])

#     WalletTransaction.objects.create(
#         wallet=wallet,
#         order=order,
#         amount=refund_amount,
#         transaction_type="credit",
#         source="order_return"
#     )

#     # Update return as refunded
#     return_request.approval_status = "refunded"
#     return_request.save(update_fields=["approval_status"])

#     # Update order payment status
#     refunded_items = order.items.filter(
#         status__in=["cancelled", "returned"]
#     ).count()

#     order.payment_status = (
#         "refunded" if refunded_items == order.items.count()
#         else "partially_refunded"
#     )
#     order.save(update_fields=["payment_status"])

#     return refund_amount

# @transaction.atomic
# def refund_order_to_wallet(order, amount,source=f"order_cancel"):
#     amount = Decimal(amount)
#     if amount <= 0:
#         return
#     max_refundable = order.original_total

#     total_already_refunded = order.refunded_amount
#     refundable_now = max_refundable - total_already_refunded
#     if refundable_now <= 0:
#         return
#     if amount > refundable_now:
#         amount = refundable_now
    
#     wallet, _ = Wallet.objects.select_for_update().get_or_create(user=order.user)

#     if WalletTransaction.objects.filter(wallet=wallet,order=order,source=source).exists():
#         return

#     order.refunded_amount += amount
#     order.save(update_fields=['refunded_amount'])

#     wallet.balance = wallet.balance + amount
#     wallet.save(update_fields=["balance"])

#     WalletTransaction.objects.create(
#         wallet=wallet,
#         order=order,
#         amount=amount,
#         transaction_type="credit",
#         source=source
#     )


# @transaction.atomic
# def refund_return_item_to_wallet(return_obj):
#     item = return_obj.item
#     order = item.order

#     if order.payment_status not in ["paid","partially_refunded"]:
#         return

#     wallet, _ = Wallet.objects.select_for_update().get_or_create(
#         user=order.user
#     )

#     if WalletTransaction.objects.filter(
#         wallet=wallet,
#         order=order,
#         source=f"order_return:{item.id}",
#         amount=item.price
#     ).exists():
#         return
#     order.refunded_amount += Decimal(item.price)
#     order.save(update_fields=['refunded_amount'])
#     wallet.balance += item.price
#     wallet.save(update_fields=["balance"])

#     WalletTransaction.objects.create(
#         wallet=wallet,
#         order=order,
#         amount=item.price,
#         transaction_type="credit",
#         source="order_return"
#     )