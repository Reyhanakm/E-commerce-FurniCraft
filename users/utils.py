import uuid
from .models import User

def generate_unique_referral_code():
    while True:
        code = uuid.uuid4().hex[:10].upper()
        if not User.objects.filter(referralcode=code).exists():
            return code
