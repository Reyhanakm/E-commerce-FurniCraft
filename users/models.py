from django.db import models
from django.contrib.auth.models import AbstractBaseUser,PermissionsMixin,BaseUserManager
from django.utils import timezone
from django.conf import settings

class UserManager(BaseUserManager):
    def create_user(self,email,password=None,**extra_fields):
        if not email:
            raise ValueError("User must have an email adddress!")
        email= self.normalize_email(email)
        user= self.model(email=email,**extra_fields)
        user.set_password(password) #hashes password
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
    referredby = models.ForeignKey('self',on_delete=models.SET_NULL,blank= True,null= True,related_name='referrals')

    image = models.ImageField(upload_to="profile_images/",default='default-user.png',null=True,blank=True)

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
    name=models.CharField(max_length=100,null=True)
    phone_no = models.CharField(max_length=15, null=True, blank=True)
    street = models.CharField(max_length=200,null=True)
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
    def __str__(self):
        return f"{self.house} - {self.district}, {self.pincode}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'is_default'], condition=models.Q(is_default=True), name='unique_default_address'),
]


    