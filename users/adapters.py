from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialAccount

User = get_user_model()

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.account.extra_data.get("email")

        if not email:
            return  

        # Check if this email already has a social account linked
        if SocialAccount.objects.filter(uid=sociallogin.account.uid, provider=sociallogin.account.provider).exists():
            return  # Already linked → allow login

        # Email exists in User model but has no social link → conflict
        if User.objects.filter(email=email).exists():
            messages.error(
                request,
                "This email is already registered using password login. Please log in using password or try another Google account."
            )
            raise ImmediateHttpResponse(redirect("user_login"))
