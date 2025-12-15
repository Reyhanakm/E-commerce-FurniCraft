from django.db import models
import uuid
from product.models import Product,ProductVariant,ProductImage
from users.models import User,UserAddress
from cloudinary.models import CloudinaryField


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

def generate_order_id():
    return "ORD-"+str(uuid.uuid4()).split('-')[0].upper()

class Orders(models.Model):
    PAYMENT_METHODS=[
        ('cash_on_delivery','Cash on Delivery'),
        ('razor_pay','Razor Pay'),
        ('wallet','Wallet')
    ]
    PAYMENT_STATUS_CHOICES=[
        ('pending','Pending'),
        ('paid','Paid'),
        ('failed','Failed')
    ]

    order_id=models.CharField(max_length=20,unique=True,default=generate_order_id)
    user= models.ForeignKey(User,related_name='user_orders',on_delete=models.CASCADE)
    address=models.ForeignKey(UserAddress,related_name='address_orders',on_delete=models.CASCADE)
    total_price_before_discount=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    total_price=models.DecimalField(max_digits=10,decimal_places=2)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    payment_method=models.CharField(choices=PAYMENT_METHODS,default='cash_on_delivery')
    delivery_charge=models.DecimalField(max_digits=6,decimal_places=2,default=0.00)
    is_paid=models.CharField(choices=PAYMENT_STATUS_CHOICES,default='pending')

    def __str__(self):
        return f"order {self.order_id} by {self.user.first_name}"
    

class OrderItem(models.Model):
    STATUS_CHOICES=[
        ('order_received','Order Received'),
        ('shipped','Shipped'),
        ('in_transit','In Transit'),
        ('delivered','Delivered'),
        ('cancelled','Cancelled'),
        ('returned','Returned')
    ]
    order=models.ForeignKey(Orders,related_name='items',on_delete=models.CASCADE)
    product=models.ForeignKey(ProductVariant,related_name='order_items',on_delete=models.CASCADE)
    quantity=models.PositiveIntegerField()
    unit_price=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    price=models.DecimalField(max_digits=10,decimal_places=2)
    cancellation_reason=models.TextField(blank=True,null=True)
    status=models.CharField(max_length=20,choices=STATUS_CHOICES,default='order_received')

    def __str__(self):
        return f"Order {self.order.order_id} - {self.product}"
    
class OrderReturn(models.Model):
    RETURN_CHOICES=[
        ('defective_product','Defective Product'),
        ('wrong_item','Wrong Item'),
        ('other','Other')
    ]
    APPROVAL_CHOICES=[
        ('pending','Pending'),
        ('refunded','Refunded'),
        ('rejected','Rejected'),
    ]
    user=models.ForeignKey(User,related_name='order_return',on_delete=models.CASCADE)
    item=models.ForeignKey(OrderItem,related_name='return_items',on_delete=models.CASCADE)
    return_status=models.CharField(max_length=100,choices=RETURN_CHOICES,blank=True,null=True)
    approval_status=models.CharField(max_length=100,choices=APPROVAL_CHOICES,blank=True,null=True)
    return_reason=models.TextField()
    image=CloudinaryField('returned_image',blank=True,null=True)
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Return request for {self.product.product.name} is {self.approval_status}"
    

class Wishlist(models.Model):
    user=models.ForeignKey(User,related_name='user_wishlist',on_delete=models.CASCADE)
    created_at=models.DateTimeField(auto_now_add=True)

    
class WishlistItem(models.Model):
    wishlist=models.ForeignKey(Wishlist,related_name='wishlist_items',on_delete=models.CASCADE)
    product=models.ForeignKey(ProductVariant,related_name='wishlist_product',on_delete=models.CASCADE)

    class Meta:
        unique_together=('wishlist','product')

    def __str__(self):
        return f"{self.product.product.name} in wishlist"
    


class Wallet(models.Model):
    user=models.ForeignKey(User,related_name='wallet_user',on_delete=models.CASCADE)
    balance=models.DecimalField(max_digits=10,decimal_places=2,default=0.00)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name}'s wallet has Rs.{self.balance} as balance."

def generate_transaction_id():
    return str(uuid.uuid4()).split('-')[0].upper()

class WalletTransaction(models.Model):
    SOURCE_CHOICES = [
        ('razorpay','Credit through Razorpay'),
        ('order_cancel','Refund - Order Cancelled'),
        ('order_return','Refund - Order Returned'),
        ('order_debit','Debited for order'),
        ('referral','Referral Bonus'),
    ]
    transaction_id=models.CharField(max_length=20,unique=True,default=generate_transaction_id)
    wallet=models.ForeignKey(Wallet,related_name="transaction",on_delete=models.CASCADE)
    order=models.ForeignKey(Orders,related_name='order_wallet',on_delete=models.CASCADE)
    amount=models.DecimalField(max_digits=10,decimal_places=2,default=0.00)
    transaction_type=models.CharField(max_length=100,choices=[
        ('credit','Credit'),('debit','Debit')
    ])
    is_paid=models.BooleanField(default=False)
    razorpay_order_id=models.CharField(max_length=255,blank=True,null=True)
    source=models.CharField(max_length=150,choices=SOURCE_CHOICES,default="null")
    created_at=models.DateTimeField(auto_now_add=True)
    
