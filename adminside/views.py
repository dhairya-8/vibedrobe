from django.shortcuts import render

def index(request):
   return render(request, 'index.html')

def login(request):
   return render(request, 'login.html')

def resetpassword(request):
   return render(request, 'resetpassword.html')

def add_product(request):
   return render(request, 'add_product.html')

def display_product(request):
   return render(request, 'display_product.html')

def edit_product(request):
   return render(request, 'edit_product.html')

def add_category(request):
   return render(request, 'add_category.html')

def add_brand(request):
   return render(request, 'add_brand.html')

def display_category(request):
   return render(request, 'display_category.html')

def display_brand(request):
   return render(request, 'display_brand.html')

def display_user(request):
   return render(request, 'display_user.html')

def display_admin(request):
   return render(request, 'display_admin.html')

def display_orders(request):
   return render(request, 'display_orders.html')

def display_orderdetails(request):
   return render(request, 'display_orderdetails.html')

def edit_orderdetails(request):
   return render(request, 'edit_orderdetails.html')

def display_cart(request):
   return render(request, 'display_cart.html')

def display_wishlist(request):
   return render(request, 'display_wishlist.html')

def display_payment(request):
   return render(request, 'display_payment.html')

def report_FBT_Report(request):
   return render(request, 'report_FBT_Report.html')

def report_customer(request):
   return render(request, 'report_customer.html')

def report_sales(request):
   return render(request, 'report_sales.html')