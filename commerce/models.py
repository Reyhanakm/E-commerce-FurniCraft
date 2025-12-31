from django.db import models
import uuid
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
    product=models.ForeignKey("product.Product",on_delete=models.CASCADE,related_name='cart_items')
    variant=models.ForeignKey("product.ProductVariant",on_delete=models.CASCADE,related_name='cart_items',null=False,blank=False)
    quantity= models.PositiveIntegerField(default=1)
    created_at= models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

def generate_order_id():
    return "ORD-"+str(uuid.uuid4()).split('-')[0].upper()

class Orders(models.Model):
    PAYMENT_METHODS=[
        ('cod','Cash on Delivery'),
        ('razorpay','Razor Pay'),
        ('wallet','Wallet')
    ]
    PAYMENT_STATUS_CHOICES=[
        ('pending','Pending'),
        ('paid','Paid'),
        ('refunded', 'Refunded'),            
        ('partially_refunded', 'Partially Refunded'),
        ('failed','Failed'),
        ('cancelled','Cancelled'),
    ]

    order_id=models.CharField(max_length=20,unique=True,default=generate_order_id)
    user= models.ForeignKey(User,related_name='user_orders',on_delete=models.CASCADE)
    address=models.ForeignKey(UserAddress,related_name='address_orders',on_delete=models.CASCADE)
    total_price_before_discount=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    coupon =models.ForeignKey("product.Coupon",null=True,blank=True,on_delete=models.SET_NULL)
    coupon_discount=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    offer_discount=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    total_price=models.DecimalField(max_digits=10,decimal_places=2)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    payment_method=models.CharField(choices=PAYMENT_METHODS,default='cod')
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True,db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True,db_index=True)
    payment_status = models.CharField(max_length=20,choices=PAYMENT_STATUS_CHOICES,default='pending')
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    delivery_charge=models.DecimalField(max_digits=6,decimal_places=2,default=0.00)

    def __str__(self):
        return f"order {self.order_id} by {self.user.first_name}"
    @property
    def is_paid(self):
        return self.payment_status
    @property
    def is_fully_cancelled(self):
        total_items = self.items.count()
        cancelled_items = self.items.filter(status='cancelled').count()
        return total_items > 0 and total_items == cancelled_items
    
    @property
    def overall_status(self):
        all_items = self.items.all() 
        
        if not all_items:
            return "Pending"

        if all(item.status == 'cancelled' for item in all_items):
            return "Cancelled"
        
        if all(item.status == 'returned' for item in all_items):
            return "Returned"

        if all(item.status == 'delivered' for item in all_items):
            return "Delivered"

        non_cancelled_items = [item for item in all_items if item.status != 'cancelled']
        if non_cancelled_items and all(item.status == 'delivered' for item in non_cancelled_items):
            return "Delivered"

        statuses = [item.status for item in all_items]
        if 'in_transit' in statuses:
            return "In Transit"
        if 'shipped' in statuses:
            return "Shipped"

        return "Processing"
    
    @property
    def can_admin_cancel(self):
        return self.items.exclude(status__in=[
            "cancelled",
            "delivered",
            "returned",
            "failed",
        ]).exists()
    

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
    product=models.ForeignKey("product.ProductVariant",related_name='order_items',on_delete=models.CASCADE)
    quantity=models.PositiveIntegerField()
    unit_price=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    price=models.DecimalField(max_digits=10,decimal_places=2)
    offer_percent = models.PositiveIntegerField(default=0)
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
    admin_note=models.TextField(blank=True,null=True)
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Return request for {self.item.product.product.name} is {self.approval_status}"
    

class Wishlist(models.Model):
    user=models.ForeignKey(User,related_name='user_wishlist',on_delete=models.CASCADE)
    created_at=models.DateTimeField(auto_now_add=True)

    
class WishlistItem(models.Model):
    wishlist=models.ForeignKey(Wishlist,related_name='wishlist_items',on_delete=models.CASCADE)
    product=models.ForeignKey("product.ProductVariant",related_name='wishlist_product',on_delete=models.CASCADE)

    class Meta:
        unique_together=('wishlist','product')

    def __str__(self):
        return f"{self.product.product.name} in wishlist"
    


class Wallet(models.Model):
    user=models.OneToOneField(User,related_name='wallet',on_delete=models.CASCADE)
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
    wallet=models.ForeignKey(Wallet,related_name="transactions",on_delete=models.CASCADE)
    order=models.ForeignKey(Orders,related_name='wallet_transactions',null=True,blank=True,on_delete=models.SET_NULL)
    amount=models.DecimalField(max_digits=10,decimal_places=2)
    transaction_type=models.CharField(max_length=100,choices=[
        ('credit','Credit'),('debit','Debit')
    ])
    razorpay_order_id=models.CharField(max_length=255,blank=True,null=True)
    source=models.CharField(max_length=150,choices=SOURCE_CHOICES,default="null")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('wallet', 'order', 'source')

