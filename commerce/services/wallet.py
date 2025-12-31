from django.db import transaction
from commerce.models import Wallet, WalletTransaction

@transaction.atomic
def pay_using_wallet(*, user, order, amount):
    wallet = Wallet.objects.select_for_update().get(user=user)

    if wallet.balance < amount:
        raise ValueError("INSUFFICIENT_BALANCE")

    wallet.balance -= amount
    wallet.save(update_fields=["balance"])

    WalletTransaction.objects.create(
        wallet=wallet,
        order=order,
        amount=amount,
        transaction_type="debit",
        source="order_debit"
    )

    order.payment_status = "paid"
    order.payment_method = "wallet"
    order.save(update_fields=["payment_status", "payment_method"])
