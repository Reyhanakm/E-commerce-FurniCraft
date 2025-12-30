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
    path('products/<int:product_id>/variants/', views.admin_variant_list, name='admin_variant_list'),
    path('products/<int:product_id>/variants/add/', views.add_variant, name='add_variant'),

    path('variants/edit/<int:id>/', views.edit_variant, name='edit_variant'),
    path('variants/delete/<int:id>/', views.delete_variant, name='delete_variant'),
    path('variants/restore/<int:id>/', views.restore_variant, name='restore_variant'),

    path('orders/',views.admin_order_list,name="order_list"),
    path("orders/<str:order_id>/",views.admin_order_details,name="order_details"),

    path("returns/",views.admin_return_list, name="admin_return_list"),
    path("returns/approve/<int:return_id>/",views.approve_return, name="approve_return"),
    path("returns/reject/<int:return_id>/",views.reject_return, name="reject_return"),


    path("offers/",views.admin_offer_list, name="admin_offer_list"),
    path("offers/product/add/", views.admin_product_offer_create, name="admin_product_offer_create"),
    path("offers/category/add/", views.admin_category_offer_create, name="admin_category_offer_create"),
    path("offers/product/<int:pk>/edit/", views.admin_product_offer_edit, name="admin_product_offer_edit"),
    path("offers/category/<int:pk>/edit/", views.admin_category_offer_edit, name="admin_category_offer_edit"),
    path("offers/product/<int:pk>/edit/", views.admin_product_offer_edit, name="admin_product_offer_edit"),
    path("offers/category/<int:pk>/edit/", views.admin_category_offer_edit, name="admin_category_offer_edit"),
    path("offers/<str:offer_type>/<int:pk>/toggle/", views.admin_offer_toggle, name="admin_offer_toggle"),

    path("coupons/",views.admin_coupon_list, name="admin_coupon_list"),
    path("coupons/create/",views.admin_coupon_create, name="admin_coupon_create"),
    path("coupons/<int:pk>/edit/",views.admin_coupon_edit, name="admin_coupon_edit"),
    path("coupons/<int:pk>/toggle/",views.admin_coupon_toggle, name="admin_coupon_toggle"),
    path("coupons/<int:pk>/delete/",views.admin_coupon_delete, name="admin_coupon_delete"),

    path("sales-report/excel/", views.sales_report_excel, name="sales_report_excel"),
    path("sales-report/",views.sales_report,name="sales_report"),
    path("sales-report/pdf/",views.sales_report_pdf,name="sales_report_pdf"),


]