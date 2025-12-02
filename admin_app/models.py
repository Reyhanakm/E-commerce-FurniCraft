from django.db import models
from cloudinary.models import CloudinaryField

class Banner(models.Model):
    name = models.CharField(max_length=100,null=True)
    image = models.CharField(max_length=255)
    status = models.BooleanField(null =False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name