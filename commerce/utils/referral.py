from django.db import transaction
from users.models import Referral
from commerce.models import Wallet, WalletTransaction

def process_referral_after_first_order(user):
    if not user.referredby:
        return

    with transaction.atomic():
        referral = (
            Referral.objects
            .select_for_update()
            .filter(referred_user=user, reward_given=False)
            .first()
        )

        if not referral:
            return

        wallet, _ = Wallet.objects.get_or_create(user=referral.referrer)
        wallet.balance += referral.reward_amount
        wallet.save(update_fields=["balance"])

        WalletTransaction.objects.create(
            wallet=wallet,
            order=None,
            amount=referral.reward_amount,
            transaction_type="credit",
            source="referral",
        )

        referral.reward_given = True
        referral.save(update_fields=["reward_given"])
