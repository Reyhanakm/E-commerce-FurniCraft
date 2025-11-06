from django import forms
from .models import Category,Product, ProductVariant, ProductImage


class AdminLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'is_deleted']  # exclude created_at
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name'}),
            'is_delted': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not name:
            raise forms.ValidationError("Category name cannot be empty.")
        return name


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name','is_deleted']


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ['material_type', 'description', 'regular_price','sales_price','stock','is_deleted']

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['product', 'image','is_primary']