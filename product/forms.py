from decimal import Decimal
from django import forms
import re
from .models import Category, Product, ProductVariant, ProductImage,ProductOffer,CategoryOffer,Coupon
from django.utils import timezone


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

class ProductOfferForm(forms.ModelForm):
    class Meta:
        model = ProductOffer
        fields = [
            "name",
            "product",
            "discount_value",
            "max_discount_amount",
            "start_date",
            "end_date",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border rounded-lg",
                "placeholder": "e.g. Diwali Sofa Offer",
            }),
            "product": forms.Select(attrs={
                "class": "w-full px-4 py-2 border rounded-lg",
            }),
            "discount_value": forms.NumberInput(attrs={
                "class": "w-full px-4 py-2 border rounded-lg",
                "step": "0.01",
            }),
            "max_discount_amount": forms.NumberInput(attrs={
                "class": "w-full px-4 py-2 border rounded-lg",
                "step": "0.01",
            }),
            "start_date": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "w-full px-4 py-2 border rounded-lg",
            }),
            "end_date": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "w-full px-4 py-2 border rounded-lg",
            }),
        }

    def clean(self):
        cleaned_data= super().clean()
        product = cleaned_data.get("product")
        percentage_value = cleaned_data.get("discount_value")
        max_cap_amount = cleaned_data.get("max_discount_amount")
        start = cleaned_data.get("start_date")
        end = cleaned_data.get("end_date")
        is_active = cleaned_data.get("is_active")

        now = timezone.now()

        if end and end <= now:
            self.add_error("end_date", "End date must be a future date.")

        if start and end and start >= end:
            self.add_error("end_date", "End date must be after start date.")
        
        if product and start and end and is_active:
            overlapping_offers = ProductOffer.objects.filter(
                product=product,
                is_active=True,
                start_date__lt=end,
                end_date__gt=start
            ).exclude(pk=self.instance.pk)

            if overlapping_offers.exists():
                self.add_error(None, f"This product already has an active offer during these dates. Please modify the dates or deactivate the existing offer.")

        if product and percentage_value is not None:
            variants = product.variants.filter(is_deleted=False)

            if variants.exists():
                original_price = min(v.sales_price for v in variants)
            else:
                original_price = Decimal('0.00')
            if percentage_value > 90:
                self.add_error("discount_value", "Discount percentage cannot exceed 90%.")
            
            if max_cap_amount:
                limit_70 = original_price * Decimal('0.70')
                if max_cap_amount > limit_70:
                    self.add_error(
                        "max_discount_amount", 
                        f"Max discount limit cannot exceed 70% of the product price (Limit: ₹{limit_70:.2f})."
                    )

        return cleaned_data
    
class CategoryOfferForm(forms.ModelForm):
    class Meta:
        model = CategoryOffer
        fields = [
            "name",
            "category",
            "discount_value",
            "max_discount_amount",
            "start_date",
            "end_date",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full px-4 py-2 border rounded-lg",
            }),
            "category": forms.Select(attrs={
                "class": "w-full px-4 py-2 border rounded-lg",
            }),
            "discount_value": forms.NumberInput(attrs={
                "class": "w-full px-4 py-2 border rounded-lg",
                "step": "0.01",
            }),
            "max_discount_amount": forms.NumberInput(attrs={
                "class": "w-full px-4 py-2 border rounded-lg",
                "step": "0.01",
            }),
            "start_date": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "w-full px-4 py-2 border rounded-lg",
            }),
            "end_date": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "w-full px-4 py-2 border rounded-lg",
            }),
        }

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        discount_value = cleaned.get("discount_value")
        max_discount_amount = cleaned.get("max_discount_amount")
        is_active = cleaned.get("is_active")

        now = timezone.now()
        if end and end <= now:
            self.add_error("end_date", "End date must be a future date.")
        if start and end:
            if start >= end:
                self.add_error("end_date", "End date must be after start date.")
        if category and start and end and is_active:
            overlapping_offers = CategoryOffer.objects.filter(
                category=category,
                is_active=True,
                start_date__lt=end,
                end_date__gt=start
            ).exclude(pk=self.instance.pk)

            if overlapping_offers.exists():
                self.add_error(None, f"This category already has an active offer during these dates.")
        
        if discount_value is not None:
            if discount_value <= 0:
                self.add_error("discount_value", "Discount percentage must be greater than 0.")
            elif discount_value > 90:
                self.add_error("discount_value", "Discount percentage cannot exceed 90%.")

        if max_discount_amount is not None:
            if max_discount_amount <= 0:
                self.add_error("max_discount_amount", "Max discount amount must be a positive value.")
        return cleaned
    
class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        exclude = ("is_deleted", "created_at", "update_at",)
        widgets = {
            "discount_type": forms.Select(attrs={"id": "id_discount_type"}),
            "maximum_discount_limit": forms.NumberInput(attrs={"id": "id_maximum_discount_limit"}),
            "valid_from": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "valid_until": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        base_class = "w-full px-4 py-2 border rounded-lg border-gray-300 focus:border-gray-800 focus:ring-gray-800"
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            field.widget.attrs.setdefault("class", "")
            field.widget.attrs["class"] += f" {base_class}"

        is_flat = False
        if self.data.get('discount_type') == 'flat':
            is_flat = True
        elif self.instance.pk and self.instance.discount_type == 'flat':
            is_flat = True

        if is_flat and 'maximum_discount_limit' in self.fields:
            self.fields['maximum_discount_limit'].widget.attrs['style'] = 'display: none !important;'
            self.fields['maximum_discount_limit'].required = False

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            exists = Coupon.objects.filter(code__iexact=code).exclude(pk=self.instance.pk).exists()
            if exists:
                raise forms.ValidationError("This coupon code already exists. Please use a unique code.")
        return code

    def clean(self):
        cleaned_data = super().clean()
        discount_type = cleaned_data.get("discount_type")
        discount_value = cleaned_data.get("discount_value")
        max_limit = cleaned_data.get('maximum_discount_limit')
        valid_from = cleaned_data.get("valid_from")
        valid_until = cleaned_data.get("valid_until")
        
        if discount_value is not None:
            if discount_value <= 0:
                self.add_error("discount_value", "Discount value must be greater than 0.")
            
            if discount_type == 'percentage':
                if discount_value > 90: 
                    self.add_error("discount_value", "Discount percentage cannot exceed 90%.")
                
                if max_limit is None or max_limit <= 0:
                    self.add_error("maximum_discount_limit", "Maximum discount limit is required for percentage coupons.")
            
            elif discount_type == 'flat':
                if discount_value > 100000: 
                     self.add_error("discount_value", "Flat discount seems too high. Please verify.")

        now = timezone.now()
        if valid_from and valid_until:
            if valid_until <= valid_from:
                self.add_error("valid_until", "Valid until must be later than valid from.")

            if valid_until <= now:
                self.add_error("valid_until", "Valid until must be a future date.")
        return cleaned_data


