from django.urls import path
from .views import *

urlpatterns = [
    # Authentication URLs
    path('login-register/', login_register_view, name='login_register'),  # Combined view
    path('logout/', user_logout, name='logout'),
    
    # Account URLs
    path('account-dashboard/', account_dashboard, name='account_dashboard'),
    path('account-orders/', account_orders, name='account_orders'),
    path('account-orders/<int:order_id>/', order_detail, name='order_detail'),
    
    # Address URLs 
    path('account-addresses/', account_addresses, name='account_addresses'),
    path('account-addresses/add/', add_address, name='add_address'),
    path('account-addresses/edit/<int:address_id>/', edit_address, name='edit_address'),
    path('account-addresses/delete/<int:address_id>/', delete_address, name='delete_address'),
    path('account-addresses/set-default/<int:address_id>/', set_default_address, name='set_default_address'),
    
    # Shop URLs
    path('', homepage, name='homepage'),
    path('homepage/', homepage, name='homepage'),
    path('shop/', shop, name='shop'),
    
    # Cart & Checkout URLs
    path('checkout/', checkout, name='checkout'),
    path('order-confirm/', orderconfirm, name='orderconfirm'),
    
    # Account URLs
    path('forgot-password/', forgotpassword, name='forgotpassword'),
    
    # Static Pages
    path('contact-us/', contactus, name='contactus'),
    path('about-us/', aboutus, name='aboutus'),
    
    # Product detail page
    path('product/<int:product_id>/', product_detail, name='product_detail'),
    path('product/<int:product_id>/submit-review/', submit_review, name='submit_review'),
    path('review/<int:review_id>/delete/', delete_review, name='delete_review'),
    path('variant/<int:variant_id>/stock/', check_variant_stock, name='check_variant_stock'),
    
    # Add to cart
    path('add-to-cart/<int:product_id>/', add_to_cart, name='add_to_cart'), 
    # Add to wishlist
    path('add-to-wishlist/<int:product_id>/', add_to_wishlist, name='add_to_wishlist'),

]