from django.urls import path
from . import views


urlpatterns=[
    path('',views.admin_login,name='admin_login'),
    path('logout/',views.admin_logout,name='admin_logout'),
    path('dashboard/',views.admin_dashboard,name='admin_dashboard'),

    path('banner/',views.banner_page,name='banner_page'),
    path('banner/edit/<int:id>/',views.edit_banner,name='edit_banner'),
    path('banner/delete/<int:id>',views.delete_banner,name='delete_banner'),


    path('categories/', views.admin_category_list, name='admin_category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/edit/<int:id>/', views.edit_category, name='edit_category'),
    path('categories/delete/<int:id>/', views.delete_category, name='delete_category'),
    path('categories/restore/<int:id>/', views.restore_category, name='restore_category'),

    path('customers/', views.customer_list, name='customer_list'),
    path('customers/toggle/<int:customer_id>/', views.toggle_block_status, name='toggle_block_status'),
    path('products/',views.admin_product_list,name='admin_product_list'),

    path('products/add',views.add_product,name='add_product'),
    path('products/edit/<int:id>/',views.edit_product,name='edit_product'),
    path('products/delete/<int:id>/',views.delete_product,name='delete_product'),
    path('products/restore/<int:id>/', views.restore_product, name='restore_product'),
    path('products/<int:product_id>/variants/', views.variant_list, name='admin_variant_list'),
    path('products/<int:product_id>/variants/add/', views.add_variant, name='add_variant'),

    path('variants/edit/<int:id>/', views.edit_variant, name='edit_variant'),
    path('variants/delete/<int:id>/', views.delete_variant, name='delete_variant'),
    path('variants/restore/<int:id>/', views.restore_variant, name='restore_variant'),


 
]