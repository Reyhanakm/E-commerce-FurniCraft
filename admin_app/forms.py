from django import forms
from .models import Banner
import re


class AdminLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
