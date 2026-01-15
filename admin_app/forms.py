from django import forms
from .models import Banner
import re


class AdminLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

class BannerForm(forms.ModelForm):
    class Meta:
        model=Banner
        fields=['name','image','status']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-100 border border-gray-300 rounded-md px-3 py-2 '
                         'focus:outline-none focus:ring-2 focus:ring-red-300',
                'placeholder': 'Enter name',
            }),
            'image': forms.HiddenInput(), 
        }
    def clean_image(self):
        image = self.cleaned_data.get('image')

        if not image:
            raise forms.ValidationError("Banner image is required.")
        if "w_400" in image:
            raise forms.ValidationError("Upload a higher resolution banner image.")
        
        return image