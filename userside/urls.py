from django.urls import path
from .views import *

urlpatterns = [
    # ==================== Authentication URLs ====================
    path('login-register/', login_register_view, name='login_register'),
    path('logout/', user_logout, name='logout'),
    path('forgot-password/', forgotpassword, name='forgotpassword'),

    # ==================== Core Application URLs ====================
    path('', homepage, name='homepage'),
    path('homepage/', homepage, name='homepage'),
    path('shop/', shop, name='shop'),
    path('product/<int:product_id>/', product_detail, name='product_detail'),

    # ==================== Cart & Checkout URLs ====================
    path('cart/', cart, name='cart'),  # Main cart page
    path('cart/items/add/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/items/update/', update_cart_item, name='update_cart_item'),
    path('cart/items/remove/<int:product_id>/<int:variant_id>/', remove_cart_item, name='remove_cart_item'),    path('checkout/', checkout, name='checkout'),
    path('order-confirm/', orderconfirm, name='orderconfirm'),

    # ==================== Product Interaction URLs ====================
    path('add-to-wishlist/<int:product_id>/', add_to_wishlist, name='add_to_wishlist'),
    path('variant/<int:variant_id>/stock/', check_variant_stock, name='check_variant_stock'),
    
    path('wishlist/', wishlist, name='wishlist'),
    path('wishlist/add/<int:product_id>/', add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:item_id>/', remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/move-to-cart/<int:item_id>/', move_to_cart, name='move_to_cart'),


    # ==================== Account Management URLs ====================
    path('account-dashboard/', account_dashboard, name='account_dashboard'),
    
    # Order related
    path('account-orders/', account_orders, name='account_orders'),
    path('account-orders/<int:order_id>/', order_detail, name='order_detail'),
    
    # Address related
    path('account-addresses/', account_addresses, name='account_addresses'),
    path('account-addresses/add/', add_address, name='add_address'),
    path('account-addresses/edit/<int:address_id>/', edit_address, name='edit_address'),
    path('account-addresses/delete/<int:address_id>/', delete_address, name='delete_address'),
    path('account-addresses/set-default/<int:address_id>/', set_default_address, name='set_default_address'),

    # ==================== Static Pages ====================
    path('contact-us/', contactus, name='contactus'),
    path('about-us/', aboutus, name='aboutus'),
]