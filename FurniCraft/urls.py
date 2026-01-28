"""
URL configuration for FurniCraft project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from .views import error_404, error_500, error_403

urlpatterns = [
    path('accounts/',include('allauth.urls')),
    path('',include('users.urls')),
    path('admin/',include('admin_app.urls')),
    path('product/',include('product.urls')),
    path('commerce/',include('commerce.urls')),

]

handler400 = "FurniCraft.views.error_400"
handler404 = 'FurniCraft.views.error_404'
handler500 = 'FurniCraft.views.error_500'
handler403 = 'FurniCraft.views.error_403'
