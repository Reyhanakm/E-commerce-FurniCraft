from django.urls import path
from . import views

urlpatterns = [
    path('cart/',views.cart_page,name='cart_page'),
    path('cart/add/product/<int:product_id>/', views.add_cart_product, name='add_cart_product'),
    path('cart/add/variant/<int:variant_id>/', views.add_cart_variant, name='add_cart_variant'),
    path('cart/increase/<int:item_id>/',views.increase_quantity,name="increase_quantity"),
    path('cart/decrease/<int:item_id>/',views.decrease_quantity,name="decrease_quantity"),
    path('cart/remove/<int:item_id>/',views.remove_cart_item,name="remove_cart_item"),
    path('cart/count/',views.cart_count,name='cart_count'),
    path('cart/cart-totals/',views.cart_totals,name='cart_totals'),

    path('checkout/',views.checkout,name='checkout'),
    path('checkout/placeorder/',views.place_order,name='place_order'),

    path('order/success/<str:order_id>/',views.order_success,name="order_success"),
    path('orders/',views.my_orders,name="my_orders"),
    path("orders/<str:order_id>/", views.user_order_detail, name="user_order_detail"),
    
]
