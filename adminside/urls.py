from django.urls import path
from . import views

urlpatterns = [

    
    path('',views.index,name='index'),    
    path('index/',views.index,name='index'),
    path('login/',views.login,name='login'),
    path('logout/',views.logout,name='logout'),
    
    # Category URLs
    path('add_category/', views.add_category, name='add_category'),
    path('edit_category/<int:id>/', views.edit_category, name='edit_category'),
    path('display_category/', views.display_category, name='display_category'),
    path('delete_category/<int:id>/', views.delete_category, name='delete_category'),
    
    # SubCategory URLs
    path('add_subcategory/', views.add_subcategory, name='add_subcategory'),
    path('edit_subcategory/<int:id>/', views.edit_subcategory, name='edit_subcategory'),
    path('display_subcategory/', views.display_subcategory, name='display_subcategory'),
    path('delete_subcategory/<int:id>/', views.delete_subcategory, name='delete_subcategory'),
      
    # Brand URLs
    path('add_brand/', views.add_brand, name='add_brand'),
    path('edit_brand/<int:id>/', views.edit_brand, name='edit_brand'),
    path('display_brand/', views.display_brand, name='display_brand'),
    path('delete_brand/<int:id>/', views.delete_brand, name='delete_brand'),
    
    # Size URLs
    path('add_size/', views.add_size, name='add_size'),
    path('edit_size/<int:id>/', views.edit_size, name='edit_size'),
    path('display_size/', views.display_size, name='display_size'),
    path('delete_size/<int:id>/', views.delete_size, name='delete_size'),
    
    # Material URLs
    path('add_material/', views.add_material, name='add_material'),
    path('edit_material/<int:id>/', views.edit_material, name='edit_material'),
    path('display_material/', views.display_material, name='display_material'),
    path('delete_material/<int:id>/', views.delete_material, name='delete_material'),
    
    # Product URLs
    path('add_product/', views.add_product, name='add_product'),
    path('edit_product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('delete_product<int:product_id>/', views.delete_product, name='delete_product'),
    path('display_product/', views.display_product, name='display_product'),

    
    # Product Variant URLs
    path('add_product_variant/<int:product_id>/', views.add_product_variant, name='add_product_variant'),
    path('display_product_variant/<int:product_id>/variants/', views.display_product_variant, name='display_product_variant'),
    path('edit_product_variant/<int:variant_id>/', views.edit_product_variant, name='edit_product_variant'),
    path('delete_product_variant/<int:id>/', views.delete_product_variant, name='delete_product_variant'),

    path('display_admin/',views.display_admin,name='display_admin'),
    path('display_orders/',views.display_orders,name='display_orders'),
    path('display_orderdetails/',views.display_orderdetails,name='display_orderdetails'),
    path('display_cart/',views.display_cart,name='display_cart'),
    path('display_wishlist/',views.display_wishlist,name='display_wishlist'),
    path('display_payment/',views.display_payment,name='display_payment'),
    path('report_FBT/',views.report_FBT,name='report_FBT'),
    path('report_customer/',views.report_customer,name='report_customer'),
    path('report_sales/',views.report_sales,name='report_sales'),
    
]