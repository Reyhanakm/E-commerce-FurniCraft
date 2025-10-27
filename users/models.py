from django.db import models
from django.contrib.auth.models import AbstractBaseUser,PermissionsMixin,BaseUserManager
from django.utils import timezone
import uuid
from datetime import timedelta
from django.conf import settings

class UserManager(BaseUserManager):
    def create_user(self,email,password=None,**extra_fields):
        if not email:
            raise ValueError("User must have an email adddress!")
        email= self.normalize_email(email)
        user= self.model(email=email,**extra_fields)
        user.set_password(password) #hashes the password
        user.save(using=self._db)
        return user
    def create_superuser(self,email,password=None,**extra_fields):
        extra_fields.setdefault('is_admin',True)
        extra_fields.setdefault('is_superuser',True)
        extra_fields.setdefault('is_staff',True)
        return self.create_user(email,password,**extra_fields)


class User(AbstractBaseUser,PermissionsMixin):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique= True,max_length= 100)
    phone_number = models.CharField(max_length=15,blank= True, null= True)
    referralcode = models.CharField(max_length=50,blank=True,null= True)
    refferdby = models.IntegerField(blank= True,null= True)

    is_admin = models.BooleanField(default= False)
    is_staff = models.BooleanField(default= False)
    is_blocked = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD ='email'
    REQUIRED_FIELDS = ['first_name','last_name']

    def __str__(self):
        return self.email
    

class UserAddress(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name='addresses')
    house = models.CharField(max_length=100)
    district = models.CharField(max_length=50)
    pincode = models.IntegerField()
    state = models.CharField(max_length=100)
    address_type = models.CharField(max_length=20)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now= True)
    is_default = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default= False)

    def __str__(self):
        return f"{self.user.email} - {self.house}"
    
class EmailOTP(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        # valid for 5 minutes
        return timezone.now() > self.created_at + timedelta(minutes=5)
    
    def __str__(self):
        return f"{self.user.email} -{self.otp}"