from django.shortcuts import render, redirect
from django.contrib import messages
from .models import *
from .decorators import admin_login_required

@admin_login_required
def index(request):
    return render(request, 'index.html')

def login(request):
    if request.method == 'POST':
        print("Login form submitted!")
        print("POST data:", request.POST)
        identifier = request.POST.get('identifier')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember')

        try:
            admin = Admin.objects.get(username=identifier)
        except Admin.DoesNotExist:
            try:
                admin = Admin.objects.get(email=identifier)
            except Admin.DoesNotExist:
                messages.error(request, 'Invalid username or email')
                return render(request, 'login.html')

        if admin.check_password(password):
            request.session['admin_id'] = admin.id
            if remember_me == 'on':
                request.session.set_expiry(1209600)  # 2 weeks
            else:
                request.session.set_expiry(0)
            
            # Redirect to 'next' or admin index
            next_url = request.GET.get('next', 'index')  # Using URL name
            return redirect(next_url)
        else:
            messages.error(request, 'Incorrect password')
    
    return render(request, 'login.html')
 
def logout(request):
    if request.method == 'POST':
        request.session.flush()
        print("Admin logged out successfully.")
        messages.success(request, 'You have been successfully logged out.')
        return redirect('login')
    return redirect('login') 
 

def add_category(request):
    if request.method == 'POST':
        print("Form submitted!")
        print("POST data:", request.POST)
        
        category_name = request.POST.get('name')
        print("Category name received:", category_name)
        
        try:
            category = Category.objects.create(
                name=category_name,
                is_active=True,
                sort_order=0
            )
            print("Category created:", category.id)
            category.save()
            messages.success(request, f"Category '{category_name}' added successfully!")
            return redirect('add_category')
            
        except Exception as e:
            print("Error:", str(e))
            messages.error(request, f"Error: {str(e)}")
    
    return render(request, 'add_category.html')
 
def resetpassword(request):
   return render(request, 'resetpassword.html')

def add_product(request):
   return render(request, 'add_product.html')

def display_product(request):
   return render(request, 'display_product.html')

def edit_product(request):
   return render(request, 'edit_product.html')

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

def report_FBT(request):
   return render(request, 'report_FBT_Report.html')

def report_customer(request):
   return render(request, 'report_customer.html')

def report_sales(request):
   return render(request, 'report_sales.html')