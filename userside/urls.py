from django.urls import path
from .views import *

urlpatterns = [
    # Authentication URLs
    path('login-register/', login_register_view, name='login_register'),  # Combined view
    path('logout/', user_logout, name='logout'),
    
    # Account URLs
    path('account-dashboard/', account_dashboard, name='account_dashboard'),
    
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