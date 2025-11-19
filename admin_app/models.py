from django.db import models
from cloudinary.models import CloudinaryField

class CategoryManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        return super().get_queryset()

    def active(self):
        # Return only active (non-deleted + status=True)
        return self.get_queryset().filter(status=True)

    def soft_delete(self, category_id):
        # Soft delete a category
        category = self.all_with_deleted().filter(id=category_id).first()
        if category:
            category.is_deleted = True
            category.save(update_fields=['is_deleted'])
            return category
        return None

    def restore(self, category_id):
        # Restore a soft-deleted category
        category = self.all_with_deleted().filter(id=category_id).first()
        if category and category.is_deleted:
            category.is_deleted = False
            category.save(update_fields=['is_deleted'])
            return category
        return None


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.CharField(max_length=500,blank=True,null=True)
    status = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    # Attach custom manager
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
        """
        Automatically handle primary image logic:
        - If this is the first image, set it as primary.
        - If marked as primary, remove primary flag from others.
        """
        if self.is_primary:
            # Make sure only one image per product is primary
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        else:
            # Automatically mark the first image as primary if none exist
            if not ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).exists():
                self.is_primary = True

        super().save(*args, **kwargs)
    
    

