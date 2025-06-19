from django.urls import path
from .views import *

urlpatterns = [
    
    path('',index,name='index'),    
    path('index/',index,name='index'),
    path('login/',login,name='login'),
    path('logout/',logout,name='logout'),
    
    # Category URLs
    path('add_category/', add_category, name='add_category'),
    path('edit_category/<int:id>/', edit_category, name='edit_category'),
    path('display_category/', display_category, name='display_category'),
    path('delete_category/<int:id>/', delete_category, name='delete_category'),
    
    # SubCategory URLs
    path('add_subcategory/', add_subcategory, name='add_subcategory'),
    path('edit_subcategory/<int:id>/', edit_subcategory, name='edit_subcategory'),
    path('display_subcategory/', display_subcategory, name='display_subcategory'),
    path('delete_subcategory/<int:id>/', delete_subcategory, name='delete_subcategory'),
      
    # Brand URLs
    path('add_brand/', add_brand, name='add_brand'),
    path('edit_brand/<int:id>/', edit_brand, name='edit_brand'),
    path('display_brand/', display_brand, name='display_brand'),
    path('delete_brand/<int:id>/', delete_brand, name='delete_brand'),
    
    # Size URLs
    path('add_size/', add_size, name='add_size'),
    path('edit_size/<int:id>/', edit_size, name='edit_size'),
    path('display_size/', display_size, name='display_size'),
    path('delete_size/<int:id>/', delete_size, name='delete_size'),
    
    # Material URLs
    path('add_material/', add_material, name='add_material'),
    path('edit_material/<int:id>/', edit_material, name='edit_material'),
    path('display_material/', display_material, name='display_material'),
    path('delete_material/<int:id>/', delete_material, name='delete_material'),
    
    # Product URLs
    path('add_product/', add_product, name='add_product'),
    path('edit_product/<int:product_id>/', edit_product, name='edit_product'),
    path('delete_product<int:product_id>/', delete_product, name='delete_product'),
    path('display_product/', display_product, name='display_product'),
  
    # Product Variant URLs
    path('add_product_variant/<int:product_id>/', add_product_variant, name='add_product_variant'),
    path('display_product_variant/<int:product_id>/variants/', display_product_variant, name='display_product_variant'),
    path('edit_product_variant/<int:variant_id>/', edit_product_variant, name='edit_product_variant'),
    path('delete_product_variant/<int:id>/', delete_product_variant, name='delete_product_variant'),

    # User URLs
    path('display_user/',display_user,name='display_user'),
    path('delete_user/<int:user_id>/',delete_user,name='delete_user'),
    path('toggle_user_status/<int:user_id>/toggle-status/', toggle_user_status, name='toggle_user_status'),
    
    # Admin URLs
    path('display_admin/',display_admin,name='display_admin'),
    
    path('display_orders/',display_orders,name='display_orders'),
    path('order_details_content/<int:order_id>/details/', order_details_content, name='order_details_content'),
     
    path('password_reset/', reset_password, name='resetpassword'),
    
    path('display_shipping/',display_shipping,name='display_shipping'),
    path('display_cart/',display_cart,name='display_cart'),
    path('display_wishlist/',display_wishlist,name='display_wishlist'),
    path('display_payment/',display_payment,name='display_payment'),
    
    # Report URLs
    path('report_FBT/',report_FBT,name='report_FBT'),
    path('report_customer/',report_customer,name='report_customer'),
    path('report_sales/',report_sales,name='report_sales'),
    
]