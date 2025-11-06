from django.urls import path
from . import views

urlpatterns=[
    path('',views.admin_login,name='admin_login'),
    path('logout/',views.admin_logout,name='admin_logout'),
    path('dashboard/',views.admin_dashboard,name='admin_dashboard'),
    path('categories/', views.admin_category_list, name='admin_category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/edit/<int:id>/', views.edit_category, name='edit_category'),
    path('categories/delete/<int:id>/', views.delete_category, name='delete_category'),
    # path('users/', views.users_list, name='users_list'),
    path('products/',views.admin_product_list,name='admin_product_list'),
    path('products/add',views.add_product,name='add_product'),
    path('products/edit/<int:id>/',views.edit_product,name='edit_product'),
    path('products/delete/<int:id>',views.delete_product,name='delete_product'),
 

]