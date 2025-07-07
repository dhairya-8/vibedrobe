from django.urls import path
from .views import *

urlpatterns = [   
    path('',homepage,name='homepage'),
    path('homepage',homepage,name='homepage'),
     # Shop page
    path('shop/', shop, name='shop'),
    
    # Product detail page
    path('product/<int:product_id>/', product_detail, name='product_detail'),
    
    # Add to cart
    path('add-to-cart/<int:product_id>/', add_to_cart, name='add_to_cart'),
    
    # Add to wishlist
    path('add-to-wishlist/<int:product_id>/', add_to_wishlist, name='add_to_wishlist'),
    
    # You might also want these:
    # path('filter-products/', filter_products, name='filter_products'),
    # path('sort-products/', sort_products, name='sort_products'),

    path('user_login',user_login,name='user_login'),
    path('register',register,name='register'),
    path('contactus',contactus,name='contactus'),
    path('aboutus',aboutus,name='aboutus'),
    path('orderconfirm',orderconfirm,name='orderconfirm'),
    path('checkout',checkout,name='checkout'),
    path('forgotpassword',forgotpassword,name='forgotpassword'),
]