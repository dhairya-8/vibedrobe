from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from .models import *
from .decorators import admin_login_required
from decimal import Decimal, InvalidOperation
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail
from django.conf import settings
import random, string, os, json
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDay
from django.core.paginator import Paginator
from django.views.decorators.http import require_GET
from datetime import datetime
from django.utils.decorators import method_decorator
from django.views import View
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db import transaction
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction

@admin_login_required
def index(request):
    today = timezone.now().date()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    
    # Order Statistics
    orders_today = Order_Master.objects.filter(order_date__date=today).count()
    orders_week = Order_Master.objects.filter(order_date__date__gte=last_week).count()
    revenue_today = Order_Master.objects.filter(
        order_date__date=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    revenue_week = Order_Master.objects.filter(
        order_date__date__gte=last_week
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Inventory Alerts
    low_stock = Product_Variants.objects.filter(stock_quantity__lt=10).count()
    out_of_stock = Product_Variants.objects.filter(stock_quantity=0).count()

    # Recent Activity
    recent_orders = Order_Master.objects.select_related('user_id').order_by('-order_date')[:5]
    recent_users = User.objects.order_by('-created_at')[:5]
    
    # Product Performance
    top_products = Product.objects.annotate(
        total_sold=Sum('variants__order_details__quantity')
    ).order_by('-total_sold')[:5]

    # Sales Trend Data (Last 7 days)
    sales_data = list(
        Order_Master.objects.filter(
            order_date__date__gte=last_week
        ).annotate(
            day=TruncDay('order_date')
        ).values('day').annotate(
            total=Sum('total_amount')
        ).order_by('day')
    )
    
    # Fill in missing days with 0 values
    sales_trend = []
    for i in range(7):
        date = last_week + timedelta(days=i)
        day_data = next((item for item in sales_data 
                        if item['day'].date() == date), {'day': date, 'total': 0})
        sales_trend.append(float(day_data['total']))

    # Order Status Distribution
    status_distribution = Order_Master.objects.values(
        'status'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    status_labels = [item['status'].title() for item in status_distribution]
    status_values = [item['count'] for item in status_distribution]

    context = {
        'orders_today': orders_today,
        'orders_week': orders_week,
        'revenue_today': revenue_today,
        'revenue_week': revenue_week,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'recent_orders': recent_orders,
        'recent_users': recent_users,
        'top_products': top_products,
        'today': today,
        'last_week': last_week,
        'sales_trend': sales_trend,
        'status_labels': status_labels,
        'status_values': status_values,
        'week_days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
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
      request.session.flush()
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
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                username = request.POST.get('username')
                email = request.POST.get('email')
                profile_image = request.FILES.get('profile_image')

                # If only profile_image is being updated (from modal)
                if profile_image and not any([first_name, last_name, username, email]):
                    admin.profile_image = profile_image
                    admin.save(update_fields=['profile_image', 'updated_at'])
                    messages.success(request, 'Profile image updated successfully!')
                    return redirect('display_admin_profile')

                # Otherwise, require all fields for full profile update
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

                if profile_image:
                    admin.profile_image = profile_image

                try:
                    admin.full_clean()
                    admin.save(update_fields=['first_name', 'last_name', 'username', 'email', 'profile_image', 'updated_at'])
                    messages.success(request, 'Profile updated successfully!')
                except ValidationError as e:
                    messages.error(request, f"Invalid data: {e}")
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
                    admin.password = new_password  # The save method will hash it
                    admin.save(update_fields=['password', 'updated_at'])
                    messages.success(request, 'Password changed successfully!')

                return redirect('display_admin_profile')

            # --- Unknown form submission ---
            else:
                messages.error(request, "Invalid form submission.")
                return redirect('display_admin_profile')

        except Admin.DoesNotExist:
            messages.error(request, "Admin profile not found.")
            return redirect('admin_login')

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
            category.sort_order = request.POST.get('sort_order', 0)
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
    categories = Category.objects.all().order_by('sort_order')
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
            subcategory.sort_order = request.POST.get('sort_order', 0)
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
    subcategories = Sub_Category.objects.select_related('category_id').all()
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
    brands = Brand.objects.all()
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
    sizes = Size.objects.all().order_by('sort_order')
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
    materials = Material.objects.all()
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
    
    paginator = Paginator(products, 30)
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

@admin_login_required
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    username = user.username
    user.delete()
    messages.success(request, f'User {username} has been deleted.')
    return redirect('display_user')

@admin_login_required
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f'User {user.username} has been {status}.')
    return redirect('display_user')

@admin_login_required
def display_orders(request):
    orders = Order_Master.objects.all().order_by('-order_date')
    return render(request, 'display_orders.html', {'orders': orders})

@admin_login_required
def order_details_content(request, order_id):
    order = get_object_or_404(Order_Master, id=order_id)
    
    context = {
        'order': order,
        'shipping_address': order.order_address_set.filter(address_type='Shipping').first(),
        'billing_address': order.order_address_set.filter(address_type='Billing').first(),
        'items': order.order_details_set.all()
    }
    return render(request, 'order_details_content.html', context)


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

@user_passes_test(lambda u: u.is_staff)
def display_wishlist(request, user_id=None):
    # If specific user_id is provided, show their wishlist
    if user_id:
        user = get_object_or_404(User, id=user_id)
        wishlists = Wishlist.objects.filter(user_id=user)
    else:
        # Show all wishlists if no user specified
        wishlists = Wishlist.objects.all()
    
    # Group by user
    wishlist_data = {}
    for wish in wishlists.select_related('user_id', 'product_id'):
        if wish.user_id not in wishlist_data:
            wishlist_data[wish.user_id] = {
                'user': wish.user_id,
                'items': [],
                'count': 0
            }
        wishlist_data[wish.user_id]['items'].append(wish)
        wishlist_data[wish.user_id]['count'] += 1
    
    context = {
        'wishlist_data': wishlist_data.values(),
        'show_all': user_id is None
    }
    
    return render(request, 'display_wishlist.html', context)

# Miscellaneous Views, PENDING

def display_payment(request):
    return render(request, 'display_payment.html')

def report_FBT(request):
    return render(request, 'report_FBT.html')

def report_customer(request):
    return render(request, 'report_customer.html')

def report_sales(request):
    return render(request, 'report_sales.html')