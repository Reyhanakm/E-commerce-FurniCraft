from django import forms
import re
from .models import Category, Product, ProductVariant, ProductImage


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['image','name', 'is_deleted']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter category name',

            }),
            'image': forms.HiddenInput(), 
            'is_deleted': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        show_deleted = kwargs.pop('show_deleted', False)
        super().__init__(*args, **kwargs)
        self.fields['image'].widget = forms.HiddenInput()
        self.fields["image"].required = True


        if not show_deleted:
            self.fields['is_deleted'].widget = forms.HiddenInput()

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not name:
            raise forms.ValidationError("Category name cannot be empty.")
        
        if not re.match(r'^[A-Za-z0-9\s\-\&\.,]+$', name):
            raise forms.ValidationError("Only letters, digits, spaces, hyphens, '&', dots, and commas are allowed.")
        if not re.search(r'[A-Za-z0-9]', name):
            raise forms.ValidationError("Category name cannot contain only special characters.")
        if name.isdigit():
            raise forms.ValidationError("Category name cannot contain only digits.")
        
        name=name.title()

        if Category.objects.filter(name__iexact=name).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("Category name already exists.")
        
        return name
    def clean_image(self):
        image = self.cleaned_data.get('image')

        if not self.instance.id or not image:
            raise forms.ValidationError("Category image is required.")
        
        return image


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'is_deleted']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter product name'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'is_deleted': forms.CheckboxInput(attrs={
                    'class': 'h-4 w-4 text-[#b82d2d] border-gray-300 rounded focus:ring-[#b82d2d]'
            }),
        }

    def __init__(self, *args, **kwargs):
        show_deleted = kwargs.pop('show_deleted', False)
        super().__init__(*args, **kwargs)
        if not show_deleted:
            self.fields['is_deleted'].widget=forms.HiddenInput()
            self.fields['is_deleted'].label=""

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not name:
            raise forms.ValidationError("Product name cannot be empty.")
        if not re.match(r'^[A-Za-z0-9\s]+$', name):
            raise forms.ValidationError("Product name should contain only letters, digits, and spaces.")
        if name.isdigit():
            raise forms.ValidationError("Product name cannot contain only digits.")
        
        name = name.title()
        if Product.objects.filter(name__iexact=name).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("Product name already exists.")

        return name
    
    def clean_image(self):
        image = self.cleaned_data.get('image')

        if not self.instance.id and not image:
            raise forms.ValidationError("Product images is required.")

        return image


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ['material_type', 'stock', 'regular_price', 'sales_price', 'description', 'is_deleted']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'is_deleted': forms.CheckboxInput(attrs={
                    'class': 'h-4 w-4 text-[#b82d2d] border-gray-300 rounded focus:ring-[#b82d2d]'
            }),
        }

    def __init__(self, *args, **kwargs):
        show_deleted = kwargs.pop('show_deleted', False)
        super().__init__(*args, **kwargs)

        if not show_deleted:
            self.fields['is_deleted'].widget=forms.HiddenInput()
            self.fields['is_deleted'].label=""

    def clean_material_type(self):
        material_type = self.cleaned_data['material_type'].strip()
        if not material_type:
            raise forms.ValidationError("Material type cannot be empty.")
        if not re.match(r'^[A-Za-z0-9\s]+$', material_type):
            raise forms.ValidationError("Material type should contain only letters, digits, and spaces.")
        if material_type.isdigit():
            raise forms.ValidationError("Material type cannot contain only digits.")
        
        material_type = material_type.title()

        if ProductVariant.objects.filter(
            product=self.instance.product,
            material_type__iexact=material_type
        ).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("Variant with this material type already exists for this product.")


        return material_type.title()

    def clean_regular_price(self):
        price = self.cleaned_data['regular_price']
        if price <= 0:
            raise forms.ValidationError("Regular price must be a positive number.")
        return price

    def clean_sales_price(self):
        price = self.cleaned_data['sales_price']
        if price < 0:
            raise forms.ValidationError("Sales price cannot be negative.")
        return price

    def clean_stock(self):
        stock = self.cleaned_data['stock']
        if stock < 0:
            raise forms.ValidationError("Stock must be a positive integer.")
        return stock


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['product', 'image', 'is_primary']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'image': MultiFileInput(attrs={'multiple': True, 'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),

        }
