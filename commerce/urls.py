from django.urls import path
from . import views
from users.views import add_address

urlpatterns = [
    path('wishlist/',views.wishlist,name="wishlist"),
    path('wishlist/items/',views.load_wishlist_items,name="load_wishlist_items"),
    path('wishlist/toggle/<int:p_id>/',views.toggle_wishlist,name="toggle_wishlist"),
    path('wishlist/move-cart/<int:p_id>/',views.move_to_cart,name="move_to_cart"),
    path('wishlist/count/',views.wishlist_count,name="wishlist_count"),

    path('cart/',views.cart_page,name='cart_page'),
    path('cart/add/product/<int:product_id>/', views.add_cart_product, name='add_cart_product'),
    path('cart/add/variant/<int:variant_id>/', views.add_cart_variant, name='add_cart_variant'),
    path('cart/increase/<int:item_id>/',views.increase_quantity,name="increase_quantity"),
    path('cart/decrease/<int:item_id>/',views.decrease_quantity,name="decrease_quantity"),
    path('cart/remove/<int:item_id>/',views.remove_cart_item,name="remove_cart_item"),
    path('cart/count/',views.cart_count,name='cart_count'),
    path('cart/cart-totals/',views.cart_totals,name='cart_totals'),

    path('stock-status/variant/<int:variant_id>/',views.stock_status_for_variant,name="stock_status_for_variant"),

    path('checkout/',views.checkout,name='checkout'),
    path('checkout/address/',add_address,name='add_address'),
    path('checkout/placeorder/',views.place_order,name='place_order'),
    path("checkout/apply-coupon/",views.apply_coupon,name="apply_coupon"),
    path('checkout/remove-coupon/',views.remove_coupon,name="remove_coupon"),

    path("pay/razorpay/<str:order_id>/", views.start_razorpay_payment, name="razorpay_start"),
    path("pay/razorpay/success/", views.razorpay_success, name="razorpay_success"),
    path("pay/razorpay/failed/", views.razorpay_failed, name="razorpay_failed"),

    path('order/payment-failed/<str:order_id>/',views.payment_failed,name='payment_failed'),
    path('order/success/<str:order_id>/',views.order_success,name="order_success"),
    path('orders-page/',views.my_orders_page,name="my_orders_page"),
    path('orders/',views.my_orders,name="my_orders"),
    path('order/item/cancel/<int:item_id>/',views.cancel_order_item,name="cancel_order_item"),
    path("orders/<str:order_id>/", views.user_order_detail, name="user_order_detail"),
    path("order/invoice/<str:order_id>/", views.download_invoice, name="download_invoice"),
    path("order/item/return/<int:item_id>/", views.request_return, name="return_request"),

    path('wallet/',views.my_wallet,name='my_wallet'),
    
]
