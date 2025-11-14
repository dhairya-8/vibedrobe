# Standard library
import os
import json
import random
import string
import csv
import io
import openpyxl
from io import BytesIO
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

# Django core
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.mail import EmailMessage, send_mail, EmailMultiAlternatives
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, F, Q, Sum, ExpressionWrapper, DecimalField, Max
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template, render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_GET, require_POST

# Django contrib
from django.contrib import messages
from django.contrib.staticfiles import finders

# Project-level
from .decorators import admin_login_required
from .models import *

from django.template.loader import get_template
from xhtml2pdf import pisa

@admin_login_required
def index(request):
    today = timezone.now().date()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    
    # Order Statistics - Only count completed orders for revenue
    orders_today = Order_Master.objects.filter(order_date__date=today).count()
    orders_week = Order_Master.objects.filter(order_date__date__gte=last_week).count()
    
    # Only count confirmed, shipped, and delivered orders for revenue
    revenue_today = Order_Master.objects.filter(
        order_date__date=today,
        status__in=['confirmed', 'shipped', 'delivered']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    revenue_week = Order_Master.objects.filter(
        order_date__date__gte=last_week,
        status__in=['confirmed', 'shipped', 'delivered']
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Calculate average order value
    avg_order_value_week = Order_Master.objects.filter(
        order_date__date__gte=last_week,
        status__in=['confirmed', 'shipped', 'delivered']
    ).aggregate(avg=Avg('total_amount'))['avg'] or 0

    # Inventory Alerts
    low_stock = Product_Variants.objects.filter(stock_quantity__lt=10, stock_quantity__gt=0).count()
    out_of_stock = Product_Variants.objects.filter(stock_quantity=0).count()

    # Recent Activity
    recent_orders = Order_Master.objects.select_related('user_id').order_by('-order_date')[:5]
    recent_users = User.objects.filter(created_at__date__gte=last_week)
    
    # Product Performance - Use Coalesce to handle None values
    top_products = Product.objects.annotate(
        total_sold=Coalesce(Sum('variants__order_details__quantity'), 0)
    ).order_by('-total_sold')[:5]

    # Sales Trend Data (Last 7 days) - Only completed orders
    sales_data = []
    orders_count_data = []
    week_days = []
    
    for i in range(7):
        date = last_week + timedelta(days=i)
        day_data = Order_Master.objects.filter(
            order_date__date=date,
            status__in=['confirmed', 'shipped', 'delivered']
        ).aggregate(
            revenue=Sum('total_amount'),
            orders=Count('id')
        )
        
        sales_data.append(float(day_data['revenue'] or 0))
        orders_count_data.append(day_data['orders'] or 0)
        week_days.append(date.strftime('%a'))  # Get abbreviated day name

    # Order Status Distribution
    status_distribution = Order_Master.objects.values(
        'status'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    status_labels = [item['status'].title() for item in status_distribution]
    status_values = [item['count'] for item in status_distribution]

    # Revenue by Category (Last 30 days)
    category_revenue = Order_Details.objects.filter(
        order_id__order_date__gte=last_month,
        order_id__status__in=['confirmed', 'shipped', 'delivered']
    ).values(
        'product_variant_id__product_id__subcategory_id__category_id__name'
    ).annotate(
        total_revenue=Sum(F('quantity') * F('unit_price'))
    ).order_by('-total_revenue')[:5]
    
    category_labels = [item['product_variant_id__product_id__subcategory_id__category_id__name'] for item in category_revenue]
    category_values = [float(item['total_revenue'] or 0) for item in category_revenue]

    # Customer Registration Trend (Last 7 days)
    user_trend = []
    user_days = []
    
    for i in range(7):
        date = last_week + timedelta(days=i)
        day_users = User.objects.filter(created_at__date=date).count()
        user_trend.append(day_users)
        user_days.append(date.strftime('%a'))

    # Top Brands by Revenue
    top_brands = Order_Details.objects.filter(
        order_id__order_date__gte=last_month,
        order_id__status__in=['confirmed', 'shipped', 'delivered']
    ).values(
        'product_variant_id__product_id__brand_id__name'
    ).annotate(
        total_revenue=Sum(F('quantity') * F('unit_price')),
        total_units=Sum('quantity')
    ).order_by('-total_revenue')[:5]
    
    brand_labels = [item['product_variant_id__product_id__brand_id__name'] for item in top_brands]
    brand_revenue = [float(item['total_revenue'] or 0) for item in top_brands]
    brand_units = [item['total_units'] for item in top_brands]

    # Payment Method Distribution
    payment_methods = Order_Master.objects.values(
        'mode_of_payment'
    ).annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('-revenue')
    
    payment_labels = [item['mode_of_payment'].upper() for item in payment_methods]
    payment_counts = [item['count'] for item in payment_methods]
    payment_revenue = [float(item['revenue'] or 0) for item in payment_methods]

    context = {
        'orders_today': orders_today,
        'orders_week': orders_week,
        'revenue_today': revenue_today,
        'revenue_week': revenue_week,
        'avg_order_value_week': avg_order_value_week,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'recent_orders': recent_orders,
        'recent_users': recent_users,
        'top_products': top_products,
        'today': today,
        'last_week': last_week,
        'sales_trend': sales_data,
        'orders_count_trend': orders_count_data,
        'status_labels': status_labels,
        'status_values': status_values,
        'week_days': week_days,
        'category_labels': category_labels,
        'category_values': category_values,
        'user_trend': user_trend,
        'user_days': user_days,
        'brand_labels': brand_labels,
        'brand_revenue': brand_revenue,
        'brand_units': brand_units,
        'payment_labels': payment_labels,
        'payment_counts': payment_counts,
        'payment_revenue': payment_revenue,
    }
    return render(request, 'index.html', context)

def login(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember')

        try:
            admin = Admin.objects.get(username=identifier)
        except Admin.DoesNotExist:
            try:
                admin = Admin.objects.get(email=identifier)
            except Admin.DoesNotExist:
                messages.info(request, 'Invalid username or email')
                return render(request, 'login.html')

        if admin.check_password(password):
            # Update last login time
            admin.last_login = timezone.now()
            admin.save(update_fields=['last_login'])
            local_time = timezone.localtime(admin.last_login)
            
            request.session['admin_id'] = admin.id
            request.session['admin_username'] = admin.username
            request.session['admin_email'] = admin.email
            request.session['admin_name'] = admin.first_name + ' ' + admin.last_name
            request.session['admin_role'] = admin.role
            print(local_time,' Admin login successfully !')
            if remember_me == 'on':
                request.session.set_expiry(1209600)  # 2 weeks
            else:
                request.session.set_expiry(0)
            

            messages.success(request, 'show_sweet_alert')           
            next_url = request.GET.get('next', 'index')
            return redirect(next_url)
        else:
            messages.error(request, 'Incorrect password')
    
    return render(request, 'login.html')
 
def logout(request):
    # Clear only admin-specific session keys
    for key in ['admin_id', 'admin_username', 'admin_email', 'admin_name', 'admin_role']:
        if key in request.session:
            del request.session[key]

    print("Admin logout successfully !")
    messages.info(request, 'You have been successfully logged out.')
    return redirect('login')

def generate_random_password(length=12):
    """Generate a random temporary password"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))

def reset_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            admin = Admin.objects.get(email=email)
            
            # Generate and set new password
            temp_password = generate_random_password()
            admin.set_password(temp_password)  
            admin.save()
            
            # Send email
            send_mail(
                'Your Temporary Password for VibeDrobe Admin',
                f'Your temporary password is: {temp_password}\n\n'
                f'Please login and change it immediately at:\n'
                f'{request.build_absolute_uri("/login/")}\n\n'
                f'Username/Email: {email}\n'
                f'Temporary Password: {temp_password}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            messages.success(request, 'Temporary password sent. Check your email.')
            return redirect('login')
            
        except Admin.DoesNotExist:
            messages.error(request, 'No admin account found with this email.')
    
    return render(request, 'resetpassword.html')

@method_decorator(admin_login_required, name='dispatch')
class AdminProfileManagement(View):
    def get(self, request):
        try:
            admin = Admin.objects.get(id=request.session.get('admin_id'))
            current_year = datetime.now().year
            account_age = current_year - admin.created_at.year

            context = {
                'admin': admin,
                'account_age': account_age,
                'current_time': timezone.now()
            
            }
            return render(request, 'display_admin_profile.html', context)
        except Admin.DoesNotExist:
            messages.error(request, "Admin profile not found.")
            return redirect('admin_login')

    def post(self, request):
        try:
            admin = Admin.objects.get(id=request.session.get('admin_id'))

            # --- Profile Information or Image Update ---
            if 'update_profile' in request.POST:
                
                # --- Get text fields ---
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                username = request.POST.get('username')
                email = request.POST.get('email')
                
                # --- Get image fields ---
                profile_image = request.FILES.get('profile_image')
                clear_image = request.POST.get('clear_profile_image') == '1'

                # Check if this is the "Personal Information" form (text fields are present)
                is_text_form_submission = any([first_name, last_name, username, email])

                if is_text_form_submission:
                    # --- Logic for "Personal Information" Form Submission ---
                    
                    if not all([first_name, last_name, username, email]):
                        messages.error(request, "All fields are required.")
                        return redirect('display_admin_profile')

                    # Check for unique username/email (exclude self)
                    if Admin.objects.exclude(id=admin.id).filter(username=username).exists():
                        messages.error(request, "Username already taken.")
                        return redirect('display_admin_profile')
                    if Admin.objects.exclude(id=admin.id).filter(email=email).exists():
                        messages.error(request, "Email already taken.")
                        return redirect('display_admin_profile')

                    admin.first_name = first_name
                    admin.last_name = last_name
                    admin.username = username
                    admin.email = email
                    
                    # This form doesn't submit an image, so profile_image will be None.
                    # We only save the text fields and leave the image as-is.
                    update_list = ['first_name', 'last_name', 'username', 'email', 'updated_at']

                    try:
                        admin.full_clean()
                        admin.save(update_fields=update_list)
                        messages.success(request, 'Profile updated successfully!')
                    except ValidationError as e:
                        # Convert validation error dict to a simpler string message
                        error_message = ". ".join([f"{k}: {v[0]}" for k, v in e.message_dict.items()])
                        messages.error(request, f"Invalid data: {error_message}")
                    
                    return redirect('display_admin_profile')

                else:
                    # --- Logic for "Profile Image Modal" Submission ---
                    
                    if profile_image:
                        # 1. User uploaded a new image
                        admin.profile_image = profile_image
                        admin.save(update_fields=['profile_image', 'updated_at'])
                        messages.success(request, 'Profile image updated successfully!')
                    
                    elif clear_image:
                        # 2. User clicked "Remove Photo" and saved
                        if admin.profile_image:
                            admin.profile_image.delete(save=True) # Deletes file and saves model
                            messages.success(request, 'Profile image removed.')
                        else:
                            messages.info(request, 'No profile image to remove.')
                    
                    else:
                        # 3. User clicked "Save" in modal with no change
                        messages.info(request, 'No changes to profile image were saved.')

                    return redirect('display_admin_profile')


            # --- Change Password ---
            elif 'change_password' in request.POST:
                current_password = request.POST.get('current_password')
                new_password = request.POST.get('new_password')
                confirm_password = request.POST.get('confirm_password')

                if not all([current_password, new_password, confirm_password]):
                    messages.error(request, "All password fields are required.")
                    return redirect('display_admin_profile')

                if not admin.check_password(current_password):
                    messages.error(request, 'Current password is not correct.')
                elif new_password != confirm_password:
                    messages.error(request, 'New passwords do not match.')
                elif len(new_password) < 8:
                    messages.error(request, 'New password must be at least 8 characters.')
                else:
                    admin.set_password(new_password) # Use set_password to ensure hashing
                    admin.save(update_fields=['password', 'updated_at'])
                    messages.success(request, 'Password changed successfully!')
                    # Note: You might want to log the user out here for security
                    # update_session_auth_hash(request, admin) # Or update session
                
                return redirect('display_admin_profile')

            # --- Unknown form submission ---
            else:
                messages.error(request, "Invalid form submission.")
                return redirect('display_admin_profile')

        except Admin.DoesNotExist:
            messages.error(request, "Admin profile not found.")
            return redirect('admin_login')
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {e}")
            return redirect('display_admin_profile')

@admin_login_required
def display_admin(request):
    admins = Admin.objects.all()
    print("Admin display page")
    print("admin data ----------->",admins)
    return render(request, 'display_admin.html', {'admins': admins})
    
# Category Views
@admin_login_required
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        sort_order = request.POST.get('sort_order',0)
        
        if not name:
            messages.error(request, "Category name is required")
            return render(request, 'add_category.html')
        
        try:
            Category.objects.create(
                name=name,
                is_active=True,
                sort_order=sort_order     
            )
            messages.success(request, f"Category '{name}' added successfully!")
            return redirect('add_category') 
            
        except Exception as e:
            if 'unique' in str(e).lower():
                messages.error(request, f"Category '{name}' already exists")
            else:
                messages.error(request, f"Error adding category: {str(e)}")
            return render(request, 'add_category.html')
    
    return render(request, 'add_category.html')
 
@admin_login_required
def edit_category(request, id):
    try:
        category = Category.objects.get(id=id)
        
        if request.method == 'POST':
            category.name = request.POST.get('name', '').strip()
            category.is_active = 'is_active' in request.POST  # Checkbox handling
            category.save()
            
            messages.success(request, "Category updated successfully!")
            return redirect('display_category')
            
        return render(request, 'edit_category.html', {'category': category})
    
    except Category.DoesNotExist:
        messages.error(request, "Category not found")
        return redirect('display_category')

@admin_login_required
def display_category(request):
    """
    Displays all categories, annotated with the count of distinct products
    linked through their subcategories.
    """
    # CORRECTED: Use 'subcategories' (plural) to match the related_name in the model.
    categories = Category.objects.annotate(
        product_count=Count('subcategories__product', distinct=True)
    ).order_by('-id')
    
    return render(request, 'display_category.html', {'categories': categories})
 
@admin_login_required
def delete_category(request, id):
    try:
        category = Category.objects.get(id=id)
        category_name = category.name
        category.delete()
        messages.info(request, f"Category '{category_name}' deleted successfully!")
    except Category.DoesNotExist:
        messages.error(request, "Category not found")
    return redirect('display_category')

# SubCategory Views
@admin_login_required
def add_subcategory(request):
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        name = request.POST.get('name', '').strip()
        sort_order = request.POST.get('sort_order', 0)
        
        if not name or not category_id:
            messages.error(request, "All fields are required")
            return redirect('add_subcategory')
        
        try:
            Sub_Category.objects.create(
                category_id=Category.objects.get(id=category_id),
                name=name,
                sort_order=sort_order,
                is_active=True
            )
            messages.success(request, "SubCategory added successfully!")
            return redirect('add_subcategory')
    
        except Exception as e:
            if 'unique' in str(e).lower():
                messages.error(request, f"Sub_Category '{name}' already exists")
            else:
                messages.error(request, f"Error adding category: {str(e)}")
            return render(request, 'add_subcategory.html')
         
    categories = Category.objects.filter(is_active=True)
    return render(request, 'add_subcategory.html', {'categories': categories})

@admin_login_required
def edit_subcategory(request, id):
    try:
        subcategory = Sub_Category.objects.get(id=id)
        categories = Category.objects.filter(is_active=True)
        
        if request.method == 'POST':
            subcategory.category_id = Category.objects.get(id=request.POST.get('category_id'))
            subcategory.name = request.POST.get('name', '').strip()
            subcategory.save()
            messages.success(request, "SubCategory updated successfully!")
            return redirect('display_subcategory')
            
        return render(request, 'edit_subcategory.html', {
            'subcategory': subcategory,
            'categories': categories
        })
    
    except Sub_Category.DoesNotExist:
        messages.error(request, "SubCategory not found")
        return redirect('display_subcategory')
    except Category.DoesNotExist:
        messages.error(request, "Invalid category selected")
        return redirect('display_subcategory')

@admin_login_required
def display_subcategory(request):
    """
    Displays all subcategories, annotated with the count of distinct products.
    """
    subcategories = Sub_Category.objects.select_related('category_id').annotate(
        product_count=Count('product', distinct=True)).order_by('-id')
    
    return render(request, 'display_subcategory.html', {'subcategories': subcategories})

@admin_login_required
def delete_subcategory(request, id):
    try:
        subcategory = Sub_Category.objects.get(id=id)
        subcategory.delete()
        messages.info(request, "SubCategory deleted successfully!")
    except Sub_Category.DoesNotExist:
        messages.error(request, "SubCategory not found")
    return redirect('display_subcategory')

# Brand Views
@admin_login_required
def add_brand(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        
        if not name:
            messages.error(request, "Brand name is required")
            return redirect('add_brand')
        
        try:
            Brand.objects.create(
                name=name,
                is_active=True
            )
            messages.success(request, "Brand added successfully!")
            return redirect('add_brand')
         
        except Exception as e:
            if 'unique' in str(e).lower():
                messages.error(request, f"Brand '{name}' already exists")
            else:
                messages.error(request, f"Error adding brand: {str(e)}")
            return render(request, 'add_brand.html')
         
    return render(request, 'add_brand.html')

@admin_login_required
def edit_brand(request, id):
    try:
        brand = Brand.objects.get(id=id)
        
        if request.method == 'POST':
            brand.name = request.POST.get('name', '').strip()
            brand.is_active = 'is_active' in request.POST 
            brand.save()
            messages.success(request, "Brand updated successfully!")
            return redirect('display_brand')
            
        return render(request, 'edit_brand.html', {'brand': brand})
    
    except Brand.DoesNotExist:
        messages.error(request, "Brand not found")
        return redirect('display_brand')

@admin_login_required
def display_brand(request):
    # Annotate each brand with the count of associated products
    brands = Brand.objects.annotate(product_count=Count('product'))
    return render(request, 'display_brand.html', {'brands': brands})

@admin_login_required
def delete_brand(request, id):
    try:
        brand = Brand.objects.get(id=id)
        brand.delete()
        messages.info(request, "Brand deleted successfully!")
    except Brand.DoesNotExist:
        messages.error(request, "Brand not found")
    return redirect('display_brand')
 
# Size Views
@admin_login_required
def add_size(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        sort_order = request.POST.get('sort_order', 0)
        
        if not name:
            messages.error(request, "Size name is required")
            return redirect('add_size')
        
        try:
            Size.objects.create(
                name=name,
                sort_order=sort_order,
                is_active=True
            )
            messages.success(request, "Size added successfully!")
            return redirect('add_size')
         
        except Exception as e:
            if 'unique' in str(e).lower():
                messages.error(request, f"Size '{name}' already exists")
            else:
                messages.error(request, f"Error adding category: {str(e)}")
            return render(request, 'add_size.html')
         
    return render(request, 'add_size.html')

@admin_login_required
def edit_size(request, id):
    try:
        size = Size.objects.get(id=id)
        
        if request.method == 'POST':
            size.name = request.POST.get('name', '').strip()
            size.sort_order = request.POST.get('sort_order', 0)
            size.is_active = 'is_active' in request.POST
            size.save()
            messages.success(request, "Size updated successfully!")
            return redirect('display_size')
            
        return render(request, 'edit_size.html', {'size': size})
    
    except Size.DoesNotExist:
        messages.error(request, "Size not found")
        return redirect('display_size')

@admin_login_required
def display_size(request):
    # Annotate each size with the count of associated product variants
    sizes = Size.objects.annotate(
        variant_count=Count('product_variants', distinct=True)
    ).order_by('sort_order')
    
    return render(request, 'display_size.html', {'sizes': sizes})

@admin_login_required
def delete_size(request, id):
    try:
        size = Size.objects.get(id=id)
        size.delete()
        messages.info(request, "Size deleted successfully!")
    except Size.DoesNotExist:
        messages.error(request, "Size not found")
    return redirect('display_size')
 
# Material Views
@admin_login_required
def add_material(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, "Material name is required")
            return redirect('add_material')
        
        try:
            Material.objects.create(
                name=name,
                description=description,
                is_active=True
            )
            messages.success(request, "Material added successfully!")
            return redirect('add_material')
         
        except Exception as e:
            if 'unique' in str(e).lower():
                messages.error(request, f"Material '{name}' already exists")
            else:
                messages.error(request, f"Error adding material: {str(e)}")
            return render(request, 'add_material.html')
    
    return render(request, 'add_material.html')

@admin_login_required
def edit_material(request, id):
    try:
        material = Material.objects.get(id=id)
        
        if request.method == 'POST':
            material.name = request.POST.get('name', '').strip()
            material.description = request.POST.get('description', '').strip()
            material.is_active = 'is_active' in request.POST 
            material.save()
            messages.success(request, "Material updated successfully!")
            return redirect('display_material')
            
        return render(request, 'edit_material.html', {'material': material})
    
    except Material.DoesNotExist:
        messages.error(request, "Material not found")
        return redirect('display_material')

@admin_login_required
def display_material(request):
    # Annotate each material with the count of associated products
    materials = Material.objects.annotate(
        product_count=Count('product', distinct=True)).order_by('-id')
    
    return render(request, 'display_material.html', {'materials': materials})

@admin_login_required
def delete_material(request, id):
    try:
        material = Material.objects.get(id=id)
        material.delete()
        messages.info(request, "Material deleted successfully!")
    except Material.DoesNotExist:
        messages.error(request, "Material not found")
    return redirect('display_material')

# Product Views
@admin_login_required
def download_json_template(request):
    template = {
        "products": [
            {
                "name": "Example Product",
                "description": "Detailed product description",
                "price": 999.99,
                "category": "Category Name",  # Must match an existing category name
                "subcategory": "Subcategory Name",  # Must match the exact category/subcategory structure:
                "fit_type": "Fit Type",  # string field, hence optional
                "brand": "Brand Name",  # Must match an existing brand name
                "color": "Color Name",
                "material": "Material Name",  # Must match an existing material name
                "gender": "Gender",  # Must match an existing gender name
                "weight": 0.5,
                "dimensions": "10x10x5 cm", 
                "base_image": "sku_name_base_image.jpg",  
                "gallery": [ 
                        {"image_path": "TSHIRT-BLK-M_1.jpg", "image_order": 1},
                        {"image_path": "TSHIRT-BLK-M_2.jpg", "image_order": 2}
                ],
                "variants": [
                    {
                        "size": "S", "sku": "PROD-001-S", "stock_quantity": 50, "additional_price": 0.00  
                    }
                ]
            }
        ]
    }
    
    response = HttpResponse(json.dumps(template, indent=4), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="product_import_template.json"'
    return response

@admin_login_required
def add_product(request):
    if request.method == 'POST' and request.FILES.get('json_file'):
        json_file = request.FILES['json_file']
        
        try:
            # === 1. PARSE AND VALIDATE JSON ===
            try:
                data = json.load(json_file)
                # Flexible input handling
                if isinstance(data, dict) and 'products' in data:
                    products_data = data['products']
                elif isinstance(data, dict):
                    products_data = [data]  # Single product
                elif isinstance(data, list):
                    products_data = data  # Array of products
                else:
                    raise ValueError("JSON must be an object, array, or object with 'products' array")
                
                if not isinstance(products_data, list):
                    products_data = [products_data]
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON file format")
            except Exception as e:
                raise ValueError(f"Invalid JSON structure: {str(e)}")

            # === 2. PRELOAD REFERENCE DATA ===
            try:
                # Case-insensitive lookups with preservation of original case
                categories = {c.name.lower(): (c.id, c.name) for c in Category.objects.all()}
                subcategories = {}
                
                for sc in Sub_Category.objects.select_related('category_id'):
                    key = f"{sc.category_id.name.lower()}/{sc.name.lower()}"
                    subcategories[key] = (sc.id, sc.name)
                
                ref_data = {
                    'categories': categories,
                    'subcategories': subcategories,
                    'brands': {b.name.lower(): (b.id, b.name) for b in Brand.objects.all()},
                    'materials': {m.name.lower(): (m.id, m.name) for m in Material.objects.all()},
                    'sizes': {s.name.lower(): (s.id, s.name) for s in Size.objects.all()},
                    'existing_skus': set(Product_Variants.objects.values_list('sku', flat=True))
                }
            except Exception as e:
                raise ValueError(f"Failed to load reference data: {str(e)}")

            # === 3. PROCESS PRODUCTS ===
            success_count = 0
            errors = []
            sku_tracker = set()
            added_products = []
            failed_products = []

            for idx, product_data in enumerate(products_data, start=1):
                product_errors = []
                product_identifier = f"Product #{idx}"
                product_name = product_data.get('name', 'Unnamed Product')
                
                if not isinstance(product_data, dict):
                    error_msg = f"{product_identifier}: Invalid product data format (must be object)"
                    errors.append(error_msg)
                    failed_products.append(f"{product_name} (Invalid format)")
                    print(f"ERROR: {error_msg}")
                    continue

                try:
                    # === 4. VALIDATE PRODUCT DATA ===
                    # 4.1 Check required fields
                    required_fields = [
                        'name', 'description', 'price',
                        'category', 'subcategory', 'brand',
                        'material', 'color', 'gender'
                    ]
                    missing = [f for f in required_fields if f not in product_data]
                    if missing:
                        raise ValueError(f"Missing required fields: {', '.join(missing)}")

                    # 4.2 Validate category/subcategory
                    category_name = product_data['category'].strip().lower()
                    subcategory_name = product_data['subcategory'].strip().lower()
                    subcategory_path = f"{category_name}/{subcategory_name}"
                    
                    if category_name not in ref_data['categories']:
                        available_categories = ', '.join(sorted([v[1] for v in ref_data['categories'].values()]))
                        raise ValueError(
                            f"Category '{product_data['category']}' not found. "
                            f"Available categories: {available_categories}"
                        )
                    
                    subcategory_info = ref_data['subcategories'].get(subcategory_path)
                    if not subcategory_info:
                        available_subcategories = []
                        for path, (sc_id, sc_name) in ref_data['subcategories'].items():
                            if category_name in path:
                                available_subcategories.append(sc_name)
                        
                        raise ValueError(
                            f"Subcategory '{product_data['subcategory']}' under category "
                            f"'{product_data['category']}' not found. Available subcategories: "
                            f"{', '.join(sorted(available_subcategories)) if available_subcategories else 'None'}"
                        )
                    subcategory_id, actual_subcategory_name = subcategory_info

                    # 4.3 Validate price
                    try:
                        price = Decimal(str(product_data['price']))
                        if price <= 0:
                            raise ValueError("Price must be greater than 0")
                    except (InvalidOperation, TypeError):
                        raise ValueError(f"Invalid price format: {product_data['price']}")

                    # 4.4 Validate brand
                    brand_name = product_data['brand'].strip().lower()
                    if brand_name not in ref_data['brands']:
                        available_brands = ', '.join(sorted([v[1] for v in ref_data['brands'].values()]))
                        raise ValueError(
                            f"Brand '{product_data['brand']}' not found. "
                            f"Available brands: {available_brands}"
                        )
                    brand_id, actual_brand_name = ref_data['brands'][brand_name]

                    # 4.5 Validate material
                    material_name = product_data['material'].strip().lower()
                    if material_name not in ref_data['materials']:
                        available_materials = ', '.join(sorted([v[1] for v in ref_data['materials'].values()]))
                        raise ValueError(
                            f"Material '{product_data['material']}' not found. "
                            f"Available materials: {available_materials}"
                        )
                    material_id, actual_material_name = ref_data['materials'][material_name]

                    # 4.6 Validate gender
                    gender = product_data['gender'].strip().lower()
                    if gender not in {'male', 'female', 'unisex'}:
                        raise ValueError(
                            f"Invalid gender '{product_data['gender']}'. "
                            "Must be 'Male', 'Female', or 'Unisex' (case insensitive)"
                        )

                    # 4.7 Validate weight if provided
                    if 'weight' in product_data and product_data['weight'] is not None:
                        try:
                            weight = Decimal(str(product_data['weight']))
                            if weight <= 0:
                                raise ValueError("Weight must be greater than 0")
                        except (InvalidOperation, TypeError):
                            raise ValueError(f"Invalid weight format: {product_data['weight']}")

                    # === 5. HANDLE IMAGES ===
                    def validate_image_path(path, folder):
                        filename = os.path.basename(path)
                        if not filename:
                            raise ValueError("Empty image filename")
                        
                        full_path = os.path.join(settings.MEDIA_ROOT, folder, filename)
                        if not os.path.exists(full_path):
                            raise ValueError(f"Image file not found: {filename}")
                        return f"{folder}/{filename}"

                    base_image = None
                    if product_data.get('base_image'):
                        try:
                            base_image = validate_image_path(product_data['base_image'], 'products/base')
                        except ValueError as e:
                            product_errors.append(f"Base image: {str(e)}")

                    # === 6. CREATE PRODUCT (WITHOUT VARIANTS FIRST) ===
                    try:
                        with transaction.atomic():
                            product = Product.objects.create(
                                name=product_data['name'],
                                description=product_data['description'],
                                price=price,
                                subcategory_id_id=subcategory_id,
                                fit_type=product_data.get('fit_type'),
                                brand_id_id=brand_id,
                                material_id_id=material_id,
                                color=product_data['color'],
                                gender=product_data['gender'],
                                weight=product_data.get('weight'),
                                dimensions=product_data.get('dimensions'),
                                base_image=base_image
                            )

                            # === 7. HANDLE GALLERY IMAGES (SEPARATE FROM VARIANTS) ===
                            gallery_errors = []
                            gallery_orders = set()
                            
                            for g_idx, gallery_item in enumerate(product_data.get('gallery', []), start=1):
                                try:
                                    if not isinstance(gallery_item, dict):
                                        raise ValueError("Gallery item must be an object")
                                    if 'image_path' not in gallery_item:
                                        raise ValueError("Missing 'image_path' in gallery item")
                                    
                                    try:
                                        image_path = validate_image_path(gallery_item['image_path'], 'products/gallery')
                                    except ValueError as e:
                                        raise ValueError(f"Image: {str(e)}")
                                    
                                    image_order = gallery_item.get('image_order', g_idx)
                                    if image_order in gallery_orders:
                                        raise ValueError(f"Duplicate image order: {image_order}")
                                    gallery_orders.add(image_order)
                                    
                                    Product_Gallery.objects.create(
                                        product_id=product,
                                        image_path=image_path,
                                        image_order=image_order
                                    )
                                except Exception as e:
                                    gallery_errors.append(f"Gallery image #{g_idx}: {str(e)}")

                            if gallery_errors:
                                product_errors.append(f"{len(gallery_errors)} gallery error(s): {', '.join(gallery_errors)}")

                            # === 8. HANDLE VARIANTS (SEPARATE TRANSACTION) ===
                            variant_errors = []
                            variant_skus = set()
                            variants_data = product_data.get('variants', [])
                            
                            if variants_data:
                                try:
                                    with transaction.atomic():
                                        for v_idx, variant in enumerate(variants_data, start=1):
                                            try:
                                                if not isinstance(variant, dict):
                                                    raise ValueError("Variant must be an object")
                                                if 'size' not in variant:
                                                    raise ValueError("Missing 'size' field in variant")
                                                if 'sku' not in variant:
                                                    raise ValueError("Missing 'sku' field in variant")
                                                
                                                variant_sku = variant['sku']
                                                if variant_sku in ref_data['existing_skus']:
                                                    raise ValueError(f"Variant SKU '{variant_sku}' already exists in database")
                                                if variant_sku in sku_tracker:
                                                    raise ValueError(f"Duplicate variant SKU '{variant_sku}' in this import")
                                                sku_tracker.add(variant_sku)
                                                
                                                if variant_sku in variant_skus:
                                                    raise ValueError(f"Duplicate variant SKU '{variant_sku}' in this product")
                                                variant_skus.add(variant_sku)

                                                size_value = variant['size']

                                                # Handle both string and numeric sizes

                                                if isinstance(size_value, (int, float)):
                                                    size_name = str(size_value).lower()
                                                else:
                                                    size_name = str(size_value).strip().lower()
                                                if size_name not in ref_data['sizes']:
                                                    available_sizes = ', '.join(sorted([v[1] for v in ref_data['sizes'].values()]))
                                                    raise ValueError(
                                                        f"Size '{variant['size']}' not found. "
                                                        f"Available sizes: {available_sizes}"
                                                    )
                                                size_id, actual_size_name = ref_data['sizes'][size_name]

                                                stock_qty = variant.get('stock_quantity', 0)
                                                try:
                                                    stock_qty = int(stock_qty)
                                                    if stock_qty < 0:
                                                        raise ValueError("Stock quantity cannot be negative")
                                                except (TypeError, ValueError):
                                                    raise ValueError(f"Invalid stock quantity: {variant.get('stock_quantity')}")

                                                additional_price = Decimal('0')
                                                if 'additional_price' in variant:
                                                    try:
                                                        additional_price = Decimal(str(variant['additional_price']))
                                                        if additional_price < 0:
                                                            raise ValueError("Additional price cannot be negative")
                                                    except (InvalidOperation, TypeError):
                                                        raise ValueError(f"Invalid additional price: {variant['additional_price']}")

                                                Product_Variants.objects.create(
                                                    product_id=product,
                                                    size_id_id=size_id,
                                                    sku=variant_sku,
                                                    stock_quantity=stock_qty,
                                                    additional_price=additional_price
                                                )
                                            except Exception as e:
                                                variant_errors.append(f"Variant #{v_idx}: {str(e)}")

                                    if variant_errors:
                                        product_errors.append(f"{len(variant_errors)} variant error(s): {', '.join(variant_errors)}")
                                        # Store variant errors in product for later reference
                                        product.variant_import_errors = "\n".join(variant_errors)
                                        product.save()

                                except Exception as e:
                                    # If variant transaction fails, we still keep the product
                                    variant_errors.append(f"Variant processing failed: {str(e)}")
                                    product_errors.append("Variant processing failed (product was still created)")
                                    product.variant_import_errors = str(e)
                                    product.save()

                    except Exception as e:
                        product_errors.append(f"Database operation failed: {str(e)}")

                    # === 9. FINAL PRODUCT VALIDATION ===
                    if product_errors:
                        raise ValueError(" | ".join(product_errors))
                    
                    success_count += 1
                    added_products.append(f"ID: {product.id} - {product.name}")

                except Exception as e:
                    error_msg = f"{product_identifier}: {str(e)}"
                    errors.append(error_msg)
                    failed_products.append(f"{product_name} - Error: {str(e)}")
                    print(f"ERROR: {error_msg}")
                    continue

            # === 10. GENERATE TERMINAL REPORT ===
            print("\n" + "="*80)
            print(" IMPORT PROCESSING REPORT ".center(80, '='))
            print("="*80)
            
            # Added products section
            print(f"\n\033[92mSUCCESSFULLY ADDED ({success_count} PRODUCTS):\033[0m")
            if added_products:
                for i, product in enumerate(added_products, 1):
                    print(f" {i}. {product}")
            else:
                print(" No products were added")
            
            # Failed products section
            print(f"\n\033[91mFAILED TO ADD ({len(failed_products)} PRODUCTS):\033[0m")
            if failed_products:
                for i, product in enumerate(failed_products, 1):
                    print(f" {i}. {product}")
            else:
                print(" No products failed")
            
            # Errors summary
            if errors:
                print("\n\033[93mERROR SUMMARY:\033[0m")
                unique_errors = set(errors)
                for i, error in enumerate(sorted(unique_errors), 1):
                    count = errors.count(error)
                    print(f" {i}. {error} (occurred {count} time{'s' if count > 1 else ''})")
            
            print("\n" + "="*80)
            print(" IMPORT PROCESS COMPLETED ".center(80, '='))
            print("="*80 + "\n")

            # === 11. WEB RESPONSE ===
            if success_count:
                messages.success(request, f"Successfully imported {success_count} product(s)")
            if errors:
                error_samples = "\n".join(f"• {e}" for e in errors[:3])
                if len(errors) > 3:
                    error_samples += f"\n• ...and {len(errors) - 3} more errors (see terminal for complete report)"
                messages.error(request, f"Failed to import {len(errors)} product(s):\n{error_samples}")

            return redirect('display_product')

        except Exception as e:
            error_msg = f"Import failed: {str(e)}"
            messages.error(request, error_msg)
            print(f"\n\033[91mCRITICAL ERROR: {error_msg}\033[0m")
            return redirect('add_product')

    # === 12. REGULAR FORM SUBMISSION ===
    elif request.method == 'POST':
        try:
            subcategory = get_object_or_404(Sub_Category, id=request.POST.get('subcategory_id'))
            brand = get_object_or_404(Brand, id=request.POST.get('brand_id'))
            material = get_object_or_404(Material, id=request.POST.get('material_id'))
            
            product = Product.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description'),
                price=request.POST.get('price'),
                subcategory_id=subcategory,
                fit_type=request.POST.get('fit_type'),
                brand_id=brand,
                material_id=material,
                color=request.POST.get('color'),
                gender=request.POST.get('gender'),
                weight=request.POST.get('weight'),
                dimensions=request.POST.get('dimensions'),
                base_image=request.FILES.get('base_image')
            )
            
            messages.success(request, 'Product added successfully! You can now add variants.')
            return redirect('add_product_variants', product_id=product.id)
        
        except Exception as e:
            error_msg = f'Error adding product: {str(e)}'
            messages.error(request, error_msg)
            print(f"ERROR: {error_msg}")
            return redirect('add_product')

    # === 13. GET REQUEST HANDLING ===
    context = {
        'categories': Category.objects.prefetch_related('subcategories').all(),
        'brands': Brand.objects.all(),
        'materials': Material.objects.all(),
        'title': 'Add Product'
    }
    return render(request, 'add_product.html', context)

@admin_login_required
@require_GET
def display_product(request):
    
    try:
        # Base queryset with select_related for performance
        products = Product.objects.all().select_related(
            'brand_id', 
            'subcategory_id__category_id'
        ).order_by('-created_at')
    except Exception as e:
        print(f"\n error fetching the products - {e}")
    
    # Get filter parameters with proper cleaning
    search_term = request.GET.get('search', '').strip()
    category_id = request.GET.get('category', '')
    brand_id = request.GET.get('brand', '')
    
    # Apply search filter if term exists
    if search_term:
        products = products.filter(
            Q(name__icontains=search_term) | 
            Q(description__icontains=search_term) |
            Q(brand_id__name__icontains=search_term)
        )
    
    # Apply category filter if valid ID
    if category_id and category_id.isdigit():
        products = products.filter(subcategory_id__category_id=int(category_id))
    
    # Apply brand filter if valid ID
    if brand_id and brand_id.isdigit():
        products = products.filter(brand_id=int(brand_id))
    
    # Annotate with variant count
    products = products.annotate(variant_count=Count('variants'))
    
    paginator = Paginator(products, 32)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all categories and brands for filters
    categories = Category.objects.all()
    brands = Brand.objects.all()
    
    context = {
        'products': page_obj,
        'categories': categories,
        'brands': brands,
        'search_term': search_term,
        'selected_category': category_id,
        'selected_brand': brand_id,
    }
    
    # Handle AJAX requests differently
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'partials/product_grid.html', context)
    
    return render(request, 'display_product.html', context)

@admin_login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        try:
            # Get related instances first
            subcategory = get_object_or_404(Sub_Category, id=request.POST.get('subcategory_id'))
            brand = get_object_or_404(Brand, id=request.POST.get('brand_id'))
            material = get_object_or_404(Material, id=request.POST.get('material_id'))
            
            # Update product fields
            product.name = request.POST.get('name')
            product.description = request.POST.get('description')
            product.price = request.POST.get('price')
            product.subcategory_id = subcategory  # Assign the instance, not just ID
            product.fit_type = request.POST.get('fit_type')
            product.brand_id = brand
            product.material_id = material
            product.color = request.POST.get('color')
            product.gender = request.POST.get('gender')
            product.weight = request.POST.get('weight')
            product.dimensions = request.POST.get('dimensions')
            
            # Handle image update
            new_image = request.FILES.get('base_image')
            if new_image:
                # Delete old image if exists
                if product.base_image:
                    if os.path.isfile(product.base_image.path):
                        os.remove(product.base_image.path)
                # Save new image
                fs = FileSystemStorage()
                filename = fs.save(new_image.name, new_image)
                product.base_image = fs.url(filename)
            

            product.updated_at = timezone.now()  # Update timestamp

            product.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('display_product')
            
        except Exception as e:
            messages.error(request, f'Error updating product: {str(e)}')
    
    # Get all categories, brands, and materials for the form
    categories = Category.objects.prefetch_related('subcategories').all()
    brands = Brand.objects.all()
    materials = Material.objects.all()
    
    context = {
        'product': product,
        'categories': categories,
        'brands': brands,
        'materials': materials,
        'title': 'Edit Product'
    }
    return render(request, 'edit_product.html', context)

@admin_login_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    try:
        # Delete associated image if exists
        if product.base_image:
            if os.path.isfile(product.base_image.path):
                os.remove(product.base_image.path)
        product.delete()
        messages.info(request, 'Product deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting product: {str(e)}')
    
    return redirect('display_product')

@admin_login_required
def product_detail_modal(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    gallery_images = Product_Gallery.objects.filter(product_id=product).order_by('image_order')
    variants = Product_Variants.objects.filter(product_id=product)
    
    context = {
        'product': product,
        'gallery_images': gallery_images,
        'variants': variants,
    }
    return render(request, 'product_detail_modal.html', context)

@admin_login_required
@require_POST
def toggle_product_status(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = not product.is_active
    product.updated_at = timezone.now()  # Update timestamp on status change
    product.save()

    # Trim product name to 30 chars (adjust as needed)
    trimmed_name = (product.name[:30] + '…') if len(product.name) > 30 else product.name

    messages.info(
        request,
        f'Product "{trimmed_name}" (ID: {product.id}) successfully '
        f'{"activated" if product.is_active else "deactivated"}.'
    )
    return redirect(request.META.get('HTTP_REFERER', 'fallback_url'))

@admin_login_required
@require_POST
def bulk_update_variants(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    updated_variants = []

    if request.method == "POST":
        for variant in product.variants.all():
            new_status = request.POST.get(f'variant_{variant.id}') == 'on'
            if variant.is_active != new_status:
                variant.is_active = new_status
                variant.save()
                # Collect size info for message
                updated_variants.append(str(variant.size_id.name))

        if updated_variants:
            # Shorten product name if too long
            short_name = product.name[:20] + ('...' if len(product.name) > 20 else '')
            sizes_str = ', '.join(updated_variants)
            messages.success(
                request,
                f"Product ID {product.id} ('{short_name}') updated for variant size(s): {sizes_str}."
            )
        else:
            messages.info(request, "No changes were made.")
        return redirect('display_product')

    messages.error(request, "Invalid request.")
    return redirect('display_product')

# Product Variant Views
@admin_login_required
def add_product_variant(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    sizes = Size.objects.filter(is_active=True)
    
    if request.method == 'POST':
        try:
            Product_Variants.objects.create(
                product_id=product,
                size_id=get_object_or_404(Size, id=request.POST.get('size_id')),
                sku=request.POST.get('sku', '').strip(),
                stock_quantity=int(request.POST.get('stock_quantity', 0)),
                reserved_quantity=int(request.POST.get('reserved_quantity', 0)),
                additional_price=Decimal(request.POST.get('additional_price', 0)),
                is_active=True
            )
            messages.success(request, "Variant added successfully!")
            if 'add_another' in request.POST:
                return redirect('add_product_variant', product_id=product_id)
            return redirect('display_product_variant', product_id=product_id)
        except Exception as e:
            messages.error(request, f"Error adding variant: {str(e)}")
    
    return render(request, 'add_product_variant.html', {
        'product': product,
        'sizes': sizes,
        'variants': Product_Variants.objects.filter(product_id=product)
    })
    
@admin_login_required
def edit_product_variant(request, variant_id):
    
    variant = get_object_or_404(Product_Variants, id=variant_id)
    sizes = Size.objects.filter(is_active=True)
    
    if request.method == 'POST':
        try:
            variant.size_id = get_object_or_404(Size, id=request.POST.get('size_id'))
            variant.sku = request.POST.get('sku', '').strip()
            variant.stock_quantity = int(request.POST.get('stock_quantity', 0))
            variant.reserved_quantity = int(request.POST.get('reserved_quantity', 0))
            variant.additional_price = Decimal(request.POST.get('additional_price', 0))
            variant.is_active = 'is_active' in request.POST
            variant.save()
            
            messages.success(request, "Variant updated successfully!")
            return redirect('display_product_variant', product_id=variant.product_id.id)
        except Exception as e:
            messages.error(request, f"Error updating variant: {str(e)}")
    
    return render(request, 'edit_product_variant.html', {
        'variant': variant,
        'sizes': sizes,
        'product': variant.product_id
    })

@admin_login_required
def delete_product_variant(request, id):
    """Delete a product variant"""
    variant = get_object_or_404(Product_Variants, id=id)
    product_id = variant.product_id.id
    
    try:
        variant.delete()
        messages.info(request, "Variant deleted successfully!")
    except Exception as e:
        messages.error(request, f"Error deleting variant: {str(e)}")
    
    return redirect('display_product_variant', product_id=product_id)
  
@admin_login_required
def display_product_variant(request, product_id):
    product = get_object_or_404(
        Product.objects.prefetch_related('variants__size_id'), 
        id=product_id
    )
    
    variants_data = []
    for variant in product.variants.all():
        variants_data.append({
            'variant': variant,
            'total_price': product.price + variant.additional_price,
            'available': variant.stock_quantity - variant.reserved_quantity,
            'size_name': variant.size_id.name
        })
    
    return render(request, 'display_product_variant.html', {
        'product': product,
        'variants_data': variants_data
    })

# User Management Views
@admin_login_required
def display_user(request):
    users = User.objects.all().order_by('-created_at')
    return render(request, 'display_user.html', {'users': users})

@transaction.atomic
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    try:
        # Delete dependent data first (child → parent order)
        Review.objects.filter(user_id=user).delete()
        RecentlyViewed.objects.filter(user_id=user).delete()
        Wishlist.objects.filter(user_id=user).delete()

        # Carts
        carts = Cart.objects.filter(user_id=user)
        Cart_Items.objects.filter(cart_id__in=carts).delete()
        carts.delete()

        # Orders
        orders = Order_Master.objects.filter(user_id=user)
        Order_Details.objects.filter(order_id__in=orders).delete()
        Order_Address.objects.filter(order_id__in=orders).delete()
        Shipping.objects.filter(order_id__in=orders).delete()
        Payment.objects.filter(order_id__in=orders).delete()
        orders.delete()

        # Addresses
        User_Address.objects.filter(user_id=user).delete()

        # Finally delete the user
        user.delete()

        messages.success(request, f"User {user.username} and all related data have been deleted successfully.")

    except Exception as e:
        messages.error(request, f"Error deleting user {user.username}: {str(e)}")

    return redirect('display_user') 

@admin_login_required
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f'User {user.username} has been {status}.')
    return redirect('display_user')

# ============================= Order and Shipping Views =============================
@admin_login_required
def display_orders(request):
    orders = Order_Master.objects.all().order_by('-order_date')
    return render(request, 'display_orders.html', {'orders': orders})

@admin_login_required
def order_details_content(request, order_id):
    order = get_object_or_404(Order_Master, id=order_id)
    
    context = {
        'order': order,
        'shipping_address': order.order_address_set.first(),
        'billing_address': order.order_address_set.first(),
        'items': order.order_details_set.all()
    }
    return render(request, 'partials/order_details_content.html', context)


@admin_login_required
def shipping_management(request):
    # Get filter parameter if exists
    status_filter = request.GET.get('status', 'all')
    
    # Get all orders with shipping information
    orders = Order_Master.objects.all().prefetch_related(
        'shipping_set', 
        'order_address_set', 
        'order_details_set',
        'user_id'
    )
    
    # Apply filter if needed
    if status_filter != 'all':
        orders = orders.filter(shipping__shipping_status=status_filter)
    
    # Order by most recent first
    orders = orders.order_by('-order_date').distinct()
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
    }
    return render(request, 'display_shipping.html', context)


@admin_login_required
def shipping_details_content(request, order_id):
    order = get_object_or_404(Order_Master, id=order_id)

    #Get or create shipping record
    shipping, created = Shipping.objects.get_or_create(order_id=order)

    context = {
        'order': order,
        'shipping': shipping,
    }
    return render(request, 'partials/shipping_details_content.html', context)


@admin_login_required
def update_shipping_status(request, order_id):
    if request.method == 'POST':
        try:
            order = get_object_or_404(Order_Master, id=order_id)
            shipping = get_object_or_404(Shipping, order_id=order)
            
            # Validate order is not cancelled
            if order.status == 'cancelled':
                messages.error(request, 'Cannot update shipping for cancelled orders.')
                return redirect('shipping_management')
            
            new_status = request.POST.get('shipping_status')
            tracking_number = request.POST.get('tracking_number', '').strip()
            excepted_delivery = request.POST.get('excepted_delivery', '').strip()
            delivery_notes = request.POST.get('delivery_notes', '').strip()
            
            # Validate required fields
            if new_status in ['shipped', 'delivered'] and not tracking_number:
                messages.error(request, 'Tracking number is required for shipped/delivered status.')
                return redirect('shipping_management')
            
            # Store old status before updating
            old_status = shipping.shipping_status
            
            # Update shipping status first
            shipping.shipping_status = new_status
            
            # Set dates based on status changes
            if new_status == 'shipped' and old_status != 'shipped':
                shipping.shipped_date = timezone.now()
            elif new_status == 'delivered' and old_status != 'delivered':
                shipping.delivered_date = timezone.now()
            
            # Update tracking number
            if tracking_number:
                # Check if tracking number already exists for another order
                existing = Shipping.objects.filter(tracking_number=tracking_number).exclude(id=shipping.id).exists()
                if existing:
                    messages.error(request, 'This tracking number is already assigned to another order.')
                    return redirect('shipping_management')
                shipping.tracking_number = tracking_number
            elif new_status in ['shipped', 'delivered'] and not shipping.tracking_number:
                # Auto-generate tracking number if not provided
                pass  # The model's save() method will handle this
            
            # Update expected delivery date
            if excepted_delivery:
                shipping.excepted_delivery = excepted_delivery
            else:
                shipping.excepted_delivery = None
            
            # Update delivery notes
            shipping.delivery_notes = delivery_notes
            
            # Save shipping record
            shipping.save()
            
            # Update the main order status using the model method
            order.update_status_based_on_shipping(new_status)
            
            messages.success(request, f'Shipping status for order #{order.order_number} updated successfully!')
            return redirect('shipping_management')
        
        except IntegrityError as e:
            print(f"Database integrity error: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, 'Database error: This tracking number might already exist.')
            return redirect('shipping_management')
        
        except Exception as e:
            print(f"Error updating shipping: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error updating shipping status: {str(e)}')
            return redirect('shipping_management')
    
    messages.error(request, 'Invalid request method.')
    return redirect('shipping_management')



# ============================= Cart and Wishlist Views =============================
@admin_login_required
def display_cart(request, user_id=None):
    # If specific user_id is provided, show their cart
    if user_id:
        user = get_object_or_404(User, id=user_id)
        carts = Cart.objects.filter(user_id=user)
    else:
        # Show all active carts if no user specified
        carts = Cart.objects.all()
    
    cart_data = []
    for cart in carts:
        cart_items = Cart_Items.objects.filter(cart_id=cart).select_related(
            'product_variant_id__product_id',
            'product_variant_id__size_id',
        )
        
        cart_subtotal = sum(item.total_price for item in cart_items)
        
        cart_data.append({
            'cart': cart,
            'user': cart.user_id,
            'items': cart_items,
            'subtotal': cart_subtotal,
            'item_count': cart_items.count()
        })
    
    context = {
        'cart_data': cart_data,
        'show_all': user_id is None
    }
    
    return render(request, 'display_cart.html', context)

@admin_login_required
def display_wishlist(request, user_id=None):

    try:
        if user_id:
            # Show specific user's wishlist
            user = get_object_or_404(User, id=user_id)
            wishlist_items = Wishlist.objects.filter(
                user_id=user
            ).select_related(
                'product_id',
                'product_id__brand_id',
                'product_id__subcategory_id'
            ).order_by('-added_at')

            wishlist_data = [{
                'user': user,
                'items': wishlist_items,
                'count': wishlist_items.count(),
                'last_updated': wishlist_items.first().added_at if wishlist_items.exists() else None
            }]
            show_all = False
        else:
            # Show all users' wishlists
            wishlist_data = []
            users_with_wishlists = User.objects.filter(
                id__in=Wishlist.objects.values_list('user_id', flat=True).distinct()
            )

            for user in users_with_wishlists:
                items = Wishlist.objects.filter(
                    user_id=user
                ).select_related(
                    'product_id',
                    'product_id__brand_id',
                    'product_id__subcategory_id'
                ).order_by('-added_at')

                if items.exists():
                    wishlist_data.append({
                        'user': user,
                        'items': items,
                        'count': items.count(),
                        'last_updated': items.first().added_at
                    })
            show_all = True

        context = {
            'wishlist_data': wishlist_data,
            'show_all': show_all,
            'title': 'All Wishlists' if not user_id else f"Wishlist for {user.get_full_name() or user.email}"
        }

        return render(request, 'display_wishlist.html', context)

    except Exception as e:
        messages.error(request, f"Error loading wishlist(s): {str(e)}")
        return redirect('display_user')

@admin_login_required
def display_user_wishlist(request, user_id):
    # Get specific user's wishlist
    user = get_object_or_404(User, id=user_id)
    wishlist_items = Wishlist.objects.filter(
        user=user
    ).select_related('product_id').order_by('-added_at')
    
    wishlist_data = [{
        'user': user,
        'items': wishlist_items,
        'count': wishlist_items.count(),
        'added_at' : wishlist_items.added_at      
        
    }]
    
    context = {
        'wishlist_data': wishlist_data,
        'show_all': False
    }
    
    return render(request, 'display_wishlist.html', context)

# ============================ Invoice and Payment Views =============================
# INVOICE VIEWS
@admin_login_required
def display_invoice_list(request):
    """
    Fetches successful orders and displays them in a list.
    """
    successful_orders = Order_Master.objects.filter(
        status__in=['shipped', 'delivered']
    ).select_related('user_id').order_by('-order_date')

    context = {
        'orders': successful_orders
    }
    return render(request, 'display_invoice.html', context)

def _get_invoice_context(order_id):
    """
    Gathers all data for an invoice.
    """
    order = get_object_or_404(Order_Master, id=order_id)
    address = Order_Address.objects.filter(order_id=order).first()
    order_items = Order_Details.objects.filter(order_id=order)

    total_gst = Decimal('0.00')
    subtotal_before_tax = Decimal('0.00')

    for item in order_items:
        if item.unit_price < 1000:
            item.base_price = (item.unit_price / Decimal('1.05'))
            item.gst_rate = 5
        else:
            item.base_price = (item.unit_price / Decimal('1.12'))
            item.gst_rate = 12
        
        gst_per_unit = item.unit_price - item.base_price
        item.total_gst_on_item = gst_per_unit * item.quantity
        total_gst += item.total_gst_on_item
        subtotal_before_tax += item.base_price * item.quantity

    return {
        'order': order,
        'order_items': order_items,
        'address': address,
        'total_gst': total_gst,
        'subtotal_before_tax': subtotal_before_tax,
    }

def view_invoice_modal(request, order_id):
    """
    Renders the HTML for the invoice modal.
    """
    context = _get_invoice_context(order_id)
    return render(request, 'partials/invoice_details_content.html', context)

# Send to user functionality
def public_invoice(request, uuid):
    """
    Publicly accessible invoice page via UUID link.
    No admin login required.
    """
    order = get_object_or_404(Order_Master, invoice_uuid=uuid)
    context = _get_invoice_context(order.id)
    return render(request, 'public_invoice.html', context)

@admin_login_required
def send_invoice_email(request, order_id):
    """
    Sends invoice email with link to download/view.
    """
    order = get_object_or_404(Order_Master, id=order_id)
    context = _get_invoice_context(order.id)

    # Generate public invoice link
    invoice_url = request.build_absolute_uri(
        reverse('invoice_page', args=[order.invoice_uuid])
    )

    # Render email template
    subject = f"Your Invoice #{order.order_number} - VibeDrobe"
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient = [order.user_id.email]

    html_content = render_to_string(
        'Emails/invoice_email.html',
        {
            'order': order,
            'address': context['address'],
            'invoice_url': invoice_url,
        }
    )

    msg = EmailMultiAlternatives(subject, "", from_email, recipient)
    msg.attach_alternative(html_content, "text/html")
    msg.send()

    return JsonResponse({"success": True, "message": "Invoice email sent successfully!"})


# PAYMENT VIEWS
@admin_login_required
def payment_management(request):
    # Auto-fail stuck pending payments (e.g., older than 30 minutes)
    Payment.auto_fail_pending_payments(minutes=30)
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    # Get all payments with related data
    payments = Payment.objects.all().select_related('order_id', 'user_id')
    
    # Apply status filter if needed
    if status_filter != 'all':
        payments = payments.filter(status=status_filter)
    
    # Apply search filter if needed
    if search_query:
        payments = payments.filter(
            Q(payment_id__icontains=search_query) |
            Q(order_id__order_number__icontains=search_query) |
            Q(user_id__email__icontains=search_query) |
            Q(user_id__first_name__icontains=search_query) |
            Q(user_id__last_name__icontains=search_query)
        )
    
    context = {
        'payments': payments,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'display_payment.html', context)

@admin_login_required
def payment_details_content(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)

    # --- ADDED LOGIC ---
    # These lines create the variables your template needs to show the correct buttons.
    # .lower() is used to make the check case-insensitive (e.g., 'COD' or 'cod' will both work).
    
    can_mark_completed = payment.payment_method.lower() == 'cod' and payment.status.lower() == 'pending'
    can_mark_refunded = payment.payment_method.lower() != 'cod' and payment.status.lower() == 'refund_initiated'
    
    # The context now includes the boolean variables for the template `if` statements.
    context = {
        'payment': payment,
        'can_mark_completed': can_mark_completed,
        'can_mark_refunded': can_mark_refunded,
    }
    
    return render(request, 'partials/payment_details_content.html', context)

@admin_login_required
def update_payment_status(request, payment_id):
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('display_payment')

    payment = get_object_or_404(Payment, id=payment_id)
    new_status = request.POST.get('payment_status')

    try:
        if new_status == 'completed' and payment.payment_method.lower() == 'cod':
            payment.status = 'completed'
            payment.save()
            
            if payment.order_id.status == 'processing':
                payment.order_id.status = 'confirmed'
                payment.order_id.save()
            
            messages.success(request, f'Payment for Order #{payment.order_id.order_number} marked as completed.')

        elif new_status == 'refunded' and payment.status == 'refund_initiated':
            refund_reason = request.POST.get('refund_reason', 'Refund processed by admin.')
            payment.status = 'refunded'
            payment.refund_amount = payment.amount
            payment.refund_reason = refund_reason
            payment.save()

            if payment.order_id.status != 'cancelled':
                payment.order_id.status = 'cancelled'
                payment.order_id.save()

            messages.success(request, f'Refund for Order #{payment.order_id.order_number} has been confirmed.')
        
        else:
            messages.warning(request, 'Invalid status update action for this payment.')

    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')

    return redirect('display_payment')

# ============================ Reports Views =============================

def report_FBT(request):
    
    # Check if this is an export request
    export_format = request.GET.get('export', None)

    # 1. Query the data from the database
    # We use select_related to efficiently get product names
    # We use annotate to calculate the combined revenue on the fly
    fbt_data = Frequently_Bought_Together.objects.select_related(
        'product_a_id', 
        'product_b_id'
    ).annotate(
        # Calculate: (Price A + Price B) * Frequency
        combined_revenue=ExpressionWrapper(
            (F('product_a_id__price') + F('product_b_id__price')) * F('frequency_count'),
            output_field=DecimalField()
        )
    ).order_by('-frequency_count') # Show most frequent first

    # 2. Handle CSV Export
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="fbt_report.csv"'
        
        writer = csv.writer(response)
        # Write the header row
        writer.writerow(['ID', 'Primary Product', 'Bought With', 'Frequency', 'Combined Revenue'])
        
        # Write data rows
        for item in fbt_data:
            writer.writerow([
                item.id,
                item.product_a_id.name,
                item.product_b_id.name,
                item.frequency_count,
                f"Rs.{item.combined_revenue:.2f}"
            ])
            
        return response

    # 3. Handle PDF Export
    if export_format == 'pdf':
        template_path = 'report_FBT_pdf.html' # We will create this template next
        context = {'fbt_data': fbt_data}
        
        # Create a Django template
        template = get_template(template_path)
        html = template.render(context)

        # Create a PDF
        result = io.BytesIO()
        pdf = pisa.CreatePDF(
            io.BytesIO(html.encode("UTF-8")), # source HTML
            dest=result                        # file handle to receive result
        )
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="fbt_report.pdf"'
            return response
        
        return HttpResponse("Error Rendering PDF", status=500)

    # 4. Handle standard HTML page view (no export)
    context = {
        'fbt_data': fbt_data
    }
    return render(request, 'report_FBT.html', context)

def report_customer(request):
    
    export_format = request.GET.get('export', None)

    # 1. Query the data
    # We only want to count orders that are confirmed, shipped, or delivered
    valid_order_status = Q(order_master__status__in=['confirmed', 'shipped', 'delivered'])

    customer_data = User.objects.annotate(
        total_orders=Count('order_master', filter=valid_order_status),
        total_spent=Sum(
            'order_master__total_amount', 
            filter=valid_order_status
        ),
        last_order_date=Max(
            'order_master__order_date', 
            filter=valid_order_status
        )
    ).order_by('-total_spent') # Show top spenders first

    # 2. Handle CSV Export
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="customer_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Customer Name', 'Email', 'Total Orders', 'Total Spent', 'Last Order Date'])
        
        for customer in customer_data:
            writer.writerow([
                customer.id,
                f"{customer.first_name} {customer.last_name}",
                customer.email,
                customer.total_orders,
                f"Rs.{customer.total_spent or 0:.2f}",
                customer.last_order_date.strftime('%Y-%m-%d') if customer.last_order_date else 'No orders'
            ])
            
        return response

    # 3. Handle PDF Export
    if export_format == 'pdf':
        template_path = 'report_customer_pdf.html' # We will create this template
        context = {'customers': customer_data}
        
        template = get_template(template_path)
        html = template.render(context)

        result = io.BytesIO()
        pdf = pisa.CreatePDF(
            io.BytesIO(html.encode("UTF-8")),
            dest=result
        )
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="customer_report.pdf"'
            return response
        
        return HttpResponse("Error Rendering PDF", status=500)

    # 4. Handle Excel Export
    if export_format == 'excel':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="customer_report.xlsx"'
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Customer Report"
        
        # Write Header
        ws.append(['ID', 'Customer Name', 'Email', 'Total Orders', 'Total Spent', 'Last Order Date'])
        
        # Write Data
        for customer in customer_data:
            last_date = customer.last_order_date.strftime('%Y-%m-%d') if customer.last_order_date else 'No orders'
            ws.append([
                customer.id,
                f"{customer.first_name} {customer.last_name}",
                customer.email,
                customer.total_orders,
                customer.total_spent or 0, # Store as number in Excel
                last_date
            ])
        
        # Format currency column
        # Note: 'E' is the 5th column (Total Spent)
        for cell in ws['E']:
            if cell.row > 1: # Skip header
                cell.number_format = '"₹"#,##0.00'
                
        wb.save(response)
        return response

    # 5. Handle standard HTML page view
    context = {
        'customers': customer_data
    }
    return render(request, 'report_customer.html', context)

def report_sales(request):
    
    export_format = request.GET.get('export', None)

    # 1. Database Query
    # Define filters for valid sales vs. returns (cancellations)
    valid_sales_filter = Q(status__in=['confirmed', 'shipped', 'delivered'])
    cancelled_sales_filter = Q(status='cancelled')

    # This is the core query.
    # It groups all orders by month and calculates the stats for that month.
    sales_data = Order_Master.objects.annotate(
        month=TruncMonth('order_date')  # 1. Group by month (e.g., '2025-01-01')
    ).values(
        'month'  # 2. Tell Django to GROUP BY this month value
    ).annotate(
        # 3. Calculate aggregates for each group
        total_orders=Count('id', filter=valid_sales_filter),
        total_revenue=Sum('total_amount', filter=valid_sales_filter),
        avg_order_value=Avg('total_amount', filter=valid_sales_filter),
        total_returns=Count('id', filter=cancelled_sales_filter)
    ).order_by('-month')  # 4. Show most recent months first

    # 2. Handle CSV Export
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Month', 'Total Orders', 'Revenue', 'Avg Order Value', 'Returns'])
        
        for sale in sales_data:
            writer.writerow([
                sale['month'].strftime('%B %Y'),
                sale['total_orders'],
                f"Rs.{sale['total_revenue'] or 0:.2f}",
                f"Rs.{sale['avg_order_value'] or 0:.2f}",
                sale['total_returns']
            ])
        return response

    # 3. Handle PDF Export
    if export_format == 'pdf':
        template_path = 'report_sales_pdf.html' # We will create this template
        context = {'sales_data': sales_data}
        
        template = get_template(template_path)
        html = template.render(context)
        result = io.BytesIO()
        
        pdf = pisa.CreatePDF(io.BytesIO(html.encode("UTF-8")), dest=result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'
            return response
        return HttpResponse("Error Rendering PDF", status=500)

    # 4. Handle Excel Export
    if export_format == 'excel':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="sales_report.xlsx"'
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sales Report"
        
        ws.append(['Month', 'Total Orders', 'Revenue', 'Avg Order Value', 'Returns'])
        
        for sale in sales_data:
            ws.append([
                sale['month'].strftime('%B %Y'),
                sale['total_orders'],
                sale['total_revenue'] or 0,
                sale['avg_order_value'] or 0,
                sale['total_returns']
            ])
        
        # Format currency columns
        for col in ['C', 'D']: # Revenue and Avg Order Value
            for cell in ws[col]:
                if cell.row > 1: # Skip header
                    cell.number_format = '"₹"#,##0.00'
                
        wb.save(response)
        return response

    # 5. Handle standard HTML page view
    context = {
        'sales_data': sales_data
    }
    return render(request, 'report_sales.html', context)