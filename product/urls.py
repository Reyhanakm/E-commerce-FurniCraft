from django.urls import path
from . import views

urlpatterns = [
    
    path('category_products/<int:id>/', views.category_products, name='category_products'),
    path('products/',views.products,name='products'),
    path('product_details/<int:id>/',views.product_details,name='product_details'),
    path("product/<int:id>/image/", views.load_product_image, name="load_product_image"),
    path("variant/<int:variant_id>/info/", views.load_variant_info, name="load_variant_info"),

    path('add-review/<int:variant_id>/',views.add_review,name="add_review"),

]
