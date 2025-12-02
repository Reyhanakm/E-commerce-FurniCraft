from django.db import models
from users.models import User
from product.models import Product,ProductVariant,ProductImage


class Cart(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name='cart')
    created_at= models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

class CartItem(models.Model):
    cart=models.ForeignKey(Cart,on_delete=models.CASCADE,related_name='items')
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='cart_items')
    variant=models.ForeignKey(ProductVariant,on_delete=models.CASCADE,related_name='cart_items',null=False,blank=False)
    quantity= models.PositiveIntegerField(default=1)
    created_at= models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


