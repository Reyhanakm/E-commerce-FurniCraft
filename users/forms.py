from django import forms
from .models import User
import re

class RegistrationForm(forms.Form):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField(max_length=100)
    phone_number = forms.CharField(max_length=15)
    password = forms.CharField(widget=forms.PasswordInput(attrs={'id':'id_password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'id':'id_confirm_password'}))
    referralcode =forms.CharField(max_length=100,required=False)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use. Please try another one.")
        return email

    
    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name.isalpha():
            raise forms.ValidationError("First name should only contain letters.")
        return first_name

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain digits only.")
        if len(phone) != 10:
            raise forms.ValidationError("Phone number must be 10 digits long.")
        return phone
    
    def clean_referralcode(self):
        referralcode = self.cleaned_data.get('referralcode')
        if referralcode:
            if not (referralcode.isalnum() and len(referralcode)==6):
                raise forms.ValidationError("Invalid referral code")
        return referralcode

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        # Password strength check
        if password:
            if len(password) < 8:
                raise forms.ValidationError("Password must be at least 8 characters long.")
            if not re.search(r"[A-Z]", password):
                raise forms.ValidationError("Password must include at least one uppercase letter.")
            if not re.search(r"[a-z]", password):
                raise forms.ValidationError("Password must include at least one lowercase letter.")
            if not re.search(r"[0-9]", password):
                raise forms.ValidationError("Password must include at least one digit.")
            if not re.search(r"[@$!%*#?&]", password):
                raise forms.ValidationError("Password must include at least one special character (@, $, !, etc.)")

        return cleaned_data


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent'
        })
    )


class ResetPasswordVerifyForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': '000000',
            'maxlength': '6',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 text-center text-2xl tracking-widest'
        })
    )

    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'id': 'new_password',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500'
        })
    )

    confirm_new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'id': 'confirm_new_password',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500'
        })
    )


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email',
            'class': 'w-full px-4 py-3 border-b border-gray-300 focus:border-blue-400 transition-colors'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'w-full px-4 py-3 pr-12 border-b border-gray-300 focus:border-blue-400 transition-colors',
            'id': 'login_password'
        })
    )

