from django.db import models
from cloudinary.models import CloudinaryField
from users.models import User
from commerce.models import Orders
from django.utils import timezone

class CategoryManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        return super().get_queryset()

    def active(self):
        return self.get_queryset().filter(status=True)

    def soft_delete(self, category_id):
        category = self.all_with_deleted().filter(id=category_id).first()
        if category:
            category.is_deleted = True
            category.save(update_fields=['is_deleted'])
            return category
        return None

    def restore(self, category_id):
        category = self.all_with_deleted().filter(id=category_id).first()
        if category and category.is_deleted:
            category.is_deleted = False
            category.save(update_fields=['is_deleted'])
            return category
        return None


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.CharField(max_length=500,unique=True)
    status = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    objects = CategoryManager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    
    
class ProductManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def all_with_deleted(self):
        return super().get_queryset()
    
    def soft_delete(self,product_id):
        p=self.all_with_deleted().filter(id=product_id).first()
        if p:
            if p.is_deleted==True:
                return None
            else:
                p.is_deleted=True
                p.save(update_fields=['is_deleted'])
                return p
        return None
    
    def restore(self,product_id):
        p=self.all_with_deleted().filter(id=product_id).first()
        if p and p.is_deleted==True:
            p.is_deleted=False
            p.save(update_fields=['is_deleted'])
            return p
        return None
    


class Product(models.Model):
    name=models.CharField(max_length=150,unique=True,null=False)
    category =models.ForeignKey(Category,on_delete=models.CASCADE,related_name='products')
    created_at =models.DateTimeField(auto_now_add=True)
    updated_at =models.DateTimeField(auto_now=True)
    is_active =models.BooleanField(default=True)
    is_deleted =models.BooleanField(default=False)

    objects=ProductManager()

    class Meta:
        ordering=['-created_at']


    def __str__(self):
        return self.name
    

class VariantManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def all_with_deleted(self):
        return super().get_queryset()
    
    def soft_delete(self,variant_id):
        v=self.all_with_deleted().filter(id=variant_id).first()
        if v:
            v.is_deleted=True
            v.save(update_fields=['is_deleted'])
            return v
        return None
    
    def restore(self,variant_id):
        v=self.all_with_deleted().filter(id=variant_id).first()
        if v and v.is_deleted==True:
            v.is_deleted=False
            v.save(update_fields=['is_deleted'])
            return v
        return None

class ProductVariant(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='variants')
    material_type=models.CharField(max_length=150,null=False)
    regular_price=models.DecimalField(max_digits=10,decimal_places=2)
    sales_price=models.DecimalField(max_digits=10,decimal_places=2)
    description=models.TextField(max_length=500)
    stock=models.IntegerField()
    is_deleted=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)


    objects=VariantManager()

    class Meta:
        ordering=['-created_at']

    def __str__(self):
        return self.material_type


class ImageManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def all_with_deleted(self):
        return super().get_queryset()
    
    def soft_delete(self,image_id):
        i=self.all_with_deleted().filter(id=image_id).first()
        if i:
            i.is_deleted=True
            i.save(update_fields=['is_deleted'])
            return i
        return None
    
    def restore(self,image_id):
        i=self.all_with_deleted().filter(id=image_id).first()
        if i and i.is_deleted==True:
            i.is_deleted=False
            i.save(update_fields=['is_deleted'])
            return i
        return None
    

class ProductImage(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='images')
    image=CloudinaryField()
    is_primary=models.BooleanField(default=False)
    is_deleted=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)

    objects=ImageManager()

    class Meta:
        ordering=['-created_at']

    def __str__(self):
        return f"Image for {self.product.name}"
    
    def save(self, *args, **kwargs):
      
        if self.is_primary:

            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        else:
            if not ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).exists():
                self.is_primary = True

        super().save(*args, **kwargs)
    
class Coupon(models.Model):
    DISCOUT_CHOICES=[
        ('percentage','Percentage'),
        ('flat','Flat Amount')
    ]
    code =models.CharField(max_length=20,unique=True)
    discount_type=models.CharField(max_length=20,choices=DISCOUT_CHOICES)
    discount_value=models.DecimalField(max_digits=10,decimal_places=2,default=0.0)
    minimum_purchase_amount=models.DecimalField(max_digits=10,decimal_places=2,default=0.0)
    maximum_discount_limit=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    usage_limit=models.PositiveIntegerField(help_text="Total usage limit across all users")
    per_user_limit = models.PositiveIntegerField(default=1,help_text="How many times a user can use this coupon")
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active=models.BooleanField(default=True)
    is_deleted=models.BooleanField(default=False)

    description = models.TextField(blank=True,null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    update_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code
    

class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon,related_name="usages",on_delete=models.CASCADE)
    user = models.ForeignKey(User,related_name="coupon_usages",on_delete=models.CASCADE)
    order = models.ForeignKey(Orders,related_name="coupon_usage",on_delete=models.SET_NULL,null=True,blank=True)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('coupon','user','order')
    
class CategoryOffer(models.Model):
    name=models.CharField(max_length=200,blank=True,null=True)
    category = models.ForeignKey(Category,related_name='category_offers',on_delete=models.CASCADE)
    discount_type = models.CharField(max_length=20,choices=[('percentage','Percentage'),('flat','Flat Amount')],
                                    default='percentage')
    discount_value=models.DecimalField(max_digits=10,decimal_places=2)
    max_discount_amount=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    start_date=models.DateTimeField()
    end_date= models.DateTimeField()
    is_active=models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True)


    class Meta:
        indexes = [
            models.Index(fields=['is_active','end_date'])
        ]
    @property
    def status(self):
        now = timezone.now()

        if not self.is_active:
            return "inactive"
        if self.start_date > now:
            return "upcoming"
        if self.end_date < now:
            return "expired"
        return "active"
    
    def __str__(self):
        return f"{self.category.name} offer"

class ProductOffer(models.Model):
    name = models.CharField(max_length=200,blank=True,null=True)
    product=models.ForeignKey(Product,related_name='product_offers',on_delete=models.CASCADE)
    discount_type = models.CharField(max_length=20,choices=[('percentage','Percentage'),('flat','Flat Amount')])
    discount_value = models.DecimalField(max_digits=10,decimal_places=2)
    max_discount_amount = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    
    start_date=models.DateTimeField()
    end_date=models.DateTimeField()
    is_active= models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True)


    class Meta:
        indexes = [
            models.Index(fields=['is_active','end_date'])
        ]

    @property
    def status(self):
        now = timezone.now()

        if not self.is_active:
            return "inactive"
        if self.start_date > now:
            return "upcoming"
        if self.end_date < now:
            return "expired"
        return "active"

    def __str__(self):
        return f"{self.product.name} offer"
    
    

