import json
import random
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

def generate_otp():
    return str(random.randint(100000,999999))

def otp_cache_key(purpose,email):
    return f"otp:{purpose}:{email}"


def send_otp_email(email,otp,subject):
    send_mail(
        subject,
        f"Welcome to Furnicraft. Your OTP is {otp}. It expires in 1 minutes.",
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

def create_and_send_otp(email,purpose,subject):
    otp=generate_otp()
    print("OTP CREATED AT:", timezone.now())

    data = {
        "otp":otp,
        "otp_created_at":timezone.now().timestamp()

    }
    cache.set(otp_cache_key(purpose,email),json.dumps(data),timeout=300)

    send_otp_email(email,otp,subject)

    return otp

def validate_otp(email,purpose,entered_otp):
    
    key=otp_cache_key(purpose,email)
    data=cache.get(key)

    if not data:
        return False,"OTP expired. Please request a new one."
    
    otp_data = json.loads(data)
    actual_otp = otp_data["otp"]

    created_at = otp_data.get("otp_created_at",0)
    elapsed = timezone.now().timestamp() - created_at

    if elapsed >300:
        cache.delete(key)
        return False,"OTP expired. Please request a new one."

    if entered_otp != actual_otp:
        return False, "Invalid OTP."
    
    cache.delete(key)
    return True,"OTP verified Successfully."


def get_remaining_otp_cooldown(email, purpose, cooldown=60):
    key = otp_cache_key(purpose, email)
    data = cache.get(key)

    if not data:
        return 0

    otp_data = json.loads(data)
    elapsed = timezone.now().timestamp() - otp_data.get("otp_created_at", 0)
    return max(0, int(cooldown - elapsed))
