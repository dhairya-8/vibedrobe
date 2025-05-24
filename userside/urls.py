from django.urls import path
from .views import *

urlpatterns = [   
    path('',homepage,name='homepage'),
    path('homepage',homepage,name='homepage'),
    path('shop',shop,name='shop'),
    path('product_detail',product_detail,name='product_detail'),
    path('cart',cart,name='cart'),
    path('user_login',user_login,name='user_login'),
    path('register',register,name='register'),
    path('contactus',contactus,name='contactus'),
    path('aboutus',aboutus,name='aboutus'),
    path('orderconfirm',orderconfirm,name='orderconfirm'),
    path('checkout',checkout,name='checkout'),
    path('forgotpassword',forgotpassword,name='forgotpassword'),
]