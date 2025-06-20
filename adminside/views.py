from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import *
from .decorators import admin_login_required
from decimal import Decimal, InvalidOperation
from django.core.files.storage import FileSystemStorage
import os, json
from datetime import datetime
from django.utils.decorators import method_decorator
from django.views import View
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.conf import settings

@admin_login_required
def index(request):
    return render(request, 'index.html')

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
                messages.error(request, 'Invalid username or email')
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
            
            next_url = request.GET.get('next', 'index') 
            return redirect(next_url)
        else:
            messages.error(request, 'Incorrect password')
    
    return render(request, 'login.html')
 
def logout(request):
      request.session.flush()
      print("Admin logout successfully !")
      messages.success(request, 'You have been successfully logged out.')
      return redirect('login')

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
def display_admin_profile(request):
    try:
        # Get the logged-in admin
        admin = Admin.objects.get(id=request.session.get('admin_id'))
        
        current_year = datetime.now().year
        account_age = current_year - admin.created_at.year

        context = {
            'admin': admin,
            'current_year': current_year,
            'account_age': account_age,  # Pass the calculated age
        }
        
        return render(request, 'display_admin_profile.html', context)
        
    except Admin.DoesNotExist:
        messages.error(request, "Admin profile not found")
        return redirect('admin_login')

@admin_login_required
def display_admin(request):
    admins = Admin.objects.all()
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
        messages.success(request, f"Category '{category_name}' deleted successfully!")
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
        messages.success(request, "SubCategory deleted successfully!")
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
        messages.success(request, "Brand deleted successfully!")
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
        messages.success(request, "Size deleted successfully!")
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
        messages.success(request, "Material deleted successfully!")
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
                "brand": "Brand Name",  # Must match an existing brand name
                "color": "Color Name",
                "material": "Material Name",  # Must match an existing material name
                "gender": "Gender",  # Must match an existing gender name
                "sku": "PROD-001", # Unique SKU for each product
                "weight": 0.5,
                "dimensions": "10x10x5 cm", 
                "base_image": "sku_name_base_image.jpg",  
                "variants": [
                    {
                        "size": "S",  # Must match an existing size name
                        "sku": "PROD-001-S", # SKU for the variant, can be auto-generated if not provided
                        "stock_quantity": 50,
                        "additional_price": 0.00  # optional
                    }
                ],
                "gallery": [ 
                        {"image_path": "TSHIRT-BLK-M_1.jpg", "image_order": 1},
                        {"image_path": "TSHIRT-BLK-M_2.jpg", "image_order": 2}
                ]
            }
        ]
    }
    
    response = HttpResponse(json.dumps(template, indent=4), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="product_import_template.json"'
    return response

@admin_login_required
def add_product(request):
    if request.method == 'POST':
        # Handle JSON file upload
        if request.FILES.get('json_file'):
            try:
                json_file = request.FILES['json_file']
                data = json.load(json_file)
                
                # Preload all reference data with proper relationship access
                categories = {c.name.lower(): c.id for c in Category.objects.all()}
                subcategories = {}
                
                # Build subcategory mapping with correct relationship access
                for sc in Sub_Category.objects.select_related('category_id'):
                    key = f"{sc.category_id.name.lower()}/{sc.name.lower()}"
                    subcategories[key] = sc.id
                
                ref_data = {
                    'categories': categories,
                    'subcategories': subcategories,
                    'brands': {b.name.lower(): b.id for b in Brand.objects.all()},
                    'materials': {m.name.lower(): m.id for m in Material.objects.all()},
                    'sizes': {s.name.lower(): s.id for s in Size.objects.all()}
                }

                success_count = 0
                errors = []

                for product_data in data.get('products', []):
                    try:
                        # === 1. VALIDATE REQUIRED FIELDS ===
                        required_fields = [
                            'name', 'description', 'price',
                            'category', 'subcategory', 'brand',
                            'material', 'color', 'gender', 'sku'
                        ]
                        missing = [f for f in required_fields if f not in product_data]
                        if missing:
                            raise ValueError(f"Missing fields: {', '.join(missing)}")

                        # === 2. FIND SUBCATEGORY ===
                        category_name = product_data['category'].strip().lower()
                        subcategory_name = product_data['subcategory'].strip().lower()
                        subcategory_path = f"{category_name}/{subcategory_name}"
                        
                        subcategory_id = ref_data['subcategories'].get(subcategory_path)
                        if not subcategory_id:
                            available = []
                            for path in ref_data['subcategories'].keys():
                                if category_name in path:
                                    available.append(path.split('/')[1])
                            raise ValueError(
                                f"Subcategory '{subcategory_name}' under category "
                                f"'{category_name}' not found. "
                                f"Available: {', '.join(available) if available else 'None'}"
                            )

                        # === 3. VALIDATE PRICE ===
                        try:
                            price = Decimal(str(product_data['price']))
                            if price <= 0:
                                raise ValueError("Price must be greater than 0")
                        except (InvalidOperation, TypeError):
                            raise ValueError(f"Invalid price format: {product_data['price']}")

                        # === 4. HANDLE IMAGES ===
                        def get_image_path(path, folder):
                            filename = os.path.basename(path)
                            full_path = os.path.join(settings.MEDIA_ROOT, folder, filename)
                            if os.path.exists(full_path):
                                return f"{folder}/{filename}"
                            raise ValueError(f"Image not found: {filename}")

                        base_image = None
                        if product_data.get('base_image'):
                            try:
                                base_image = get_image_path(product_data['base_image'], 'products/base')
                            except ValueError as e:
                                messages.warning(request, f"Product {product_data['sku']}: {str(e)}")

                        # === 5. CREATE PRODUCT ===
                        product = Product.objects.create(
                            name=product_data['name'],
                            description=product_data['description'],
                            price=price,
                            subcategory_id_id=subcategory_id,
                            brand_id_id=ref_data['brands'][product_data['brand'].strip().lower()],
                            material_id_id=ref_data['materials'][product_data['material'].strip().lower()],
                            color=product_data['color'],
                            gender=product_data['gender'],
                            sku=product_data['sku'],
                            weight=product_data.get('weight'),
                            dimensions=product_data.get('dimensions'),
                            base_image=base_image
                        )

                        # === 6. HANDLE VARIANTS ===
                        variant_errors = []
                        for variant in product_data.get('variants', []):
                            try:
                                size_name = variant.get('size', '').strip().lower()
                                size_id = ref_data['sizes'].get(size_name)
                                if not size_id:
                                    available_sizes = ', '.join(sorted(ref_data['sizes'].keys()))
                                    raise ValueError(f"Size '{variant.get('size')}' not found. Available: {available_sizes}")

                                Product_Variants.objects.create(
                                    product_id=product,
                                    size_id_id=size_id,
                                    sku=variant.get('sku', f"{product_data['sku']}-{size_name.upper()}"),
                                    stock_quantity=int(variant.get('stock_quantity', 0)),
                                    additional_price=Decimal(str(variant.get('additional_price', 0)))
                                )
                            except Exception as e:
                                variant_errors.append(str(e))

                        if variant_errors:
                            messages.warning(
                                request,
                                f"Product {product_data['sku']}: {len(variant_errors)} "
                                f"variant error(s): {', '.join(variant_errors)}"
                            )

                        # === 7. HANDLE GALLERY ===
                        gallery_errors = []
                        for gallery_item in product_data.get('gallery', []):
                            try:
                                image_path = get_image_path(gallery_item['image_path'], 'products/gallery')
                                Product_Gallery.objects.create(
                                    product_id=product,
                                    image_path=image_path,
                                    image_order=gallery_item.get('image_order', 1)
                                )
                            except Exception as e:
                                gallery_errors.append(str(e))

                        if gallery_errors:
                            messages.warning(
                                request,
                                f"Product {product_data['sku']}: {len(gallery_errors)} "
                                f"gallery error(s): {', '.join(gallery_errors)}"
                            )

                        success_count += 1

                    except Exception as e:
                        errors.append(f"{product_data.get('sku', 'Unknown')}: {str(e)}")
                        continue

                # Final report
                if success_count:
                    messages.success(request, f"Successfully imported {success_count} product(s)")
                if errors:
                    messages.error(
                        request,
                        f"Failed to import {len(errors)} product(s). Issues: " +
                        "; ".join(errors[:3]) + 
                        ("..." if len(errors) > 3 else "")
                    )

                return redirect('display_product')

            except json.JSONDecodeError:
                messages.error(request, "Invalid JSON file format")
            except Exception as e:
                messages.error(request, f"File processing failed: {str(e)}")
            return redirect('add_product')

        # Handle regular form submission
        else:
            try:
                subcategory = get_object_or_404(Sub_Category, id=request.POST.get('subcategory_id'))
                brand = get_object_or_404(Brand, id=request.POST.get('brand_id'))
                material = get_object_or_404(Material, id=request.POST.get('material_id'))
                
                product = Product.objects.create(
                    name=request.POST.get('name'),
                    description=request.POST.get('description'),
                    price=request.POST.get('price'),
                    subcategory_id=subcategory,
                    brand_id=brand,
                    material_id=material,
                    color=request.POST.get('color'),
                    gender=request.POST.get('gender'),
                    sku=request.POST.get('sku'),
                    weight=request.POST.get('weight'),
                    dimensions=request.POST.get('dimensions'),
                    base_image=request.FILES.get('base_image')
                )
                
                messages.success(request, 'Product added successfully!')
                return redirect('display_product')
            
            except Exception as e:
                messages.error(request, f'Error adding product: {str(e)}')
    
    # GET request handling
    context = {
        'categories': Category.objects.prefetch_related('subcategories').all(),
        'brands': Brand.objects.all(),
        'materials': Material.objects.all(),
        'title': 'Add Product'
    }
    return render(request, 'add_product.html', context)
    if request.method == 'POST':
        # Handle JSON file upload
        if request.FILES.get('json_file'):
            try:
                json_file = request.FILES['json_file']
                data = json.load(json_file)
                
                # Preload all reference data (optimization)
                ref_data = {
                    'categories': {c.name.lower(): c.id for c in Category.objects.all()},
                    'subcategories': {
                        f"{s.category.name.lower()}/{s.name.lower()}": s.id 
                        for s in Sub_Category.objects.select_related('category_id')
                    },
                    'brands': {b.name.lower(): b.id for b in Brand.objects.all()},
                    'materials': {m.name.lower(): m.id for m in Material.objects.all()},
                    'sizes': {s.name.lower(): s.id for s in Size.objects.all()}
                }

                success_count = 0
                skipped_products = []

                for idx, product_data in enumerate(data.get('products', []), start=1):
                    try:
                        # ===== 1. VALIDATE REQUIRED FIELDS =====
                        required_fields = [
                            'name', 'description', 'price',
                            'category', 'subcategory', 'brand',
                            'material', 'color', 'gender', 'sku'
                        ]
                        missing_fields = [f for f in required_fields if f not in product_data]
                        if missing_fields:
                            raise ValueError(f"Missing fields: {', '.join(missing_fields)}")

                        # ===== 2. CONVERT NAMES TO IDs =====
                        # Subcategory (format: "category/subcategory")
                        subcategory_path = f"{product_data['category'].lower()}/{product_data['subcategory'].lower()}"
                        subcategory_id = ref_data['subcategories'].get(subcategory_path)
                        if not subcategory_id:
                            raise ValueError(
                                f"Subcategory '{product_data['subcategory']}' under "
                                f"category '{product_data['category']}' not found"
                            )

                        # Other fields
                        brand_id = ref_data['brands'].get(product_data['brand'].lower())
                        material_id = ref_data['materials'].get(product_data['material'].lower())

                        if None in [subcategory_id, brand_id, material_id]:
                            missing = []
                            if not subcategory_id: missing.append("subcategory")
                            if not brand_id: missing.append("brand")
                            if not material_id: missing.append("material")
                            raise ValueError(f"Reference not found: {', '.join(missing)}")

                        # ===== 3. VALIDATE PRICE =====
                        try:
                            price = Decimal(str(product_data['price']))
                            if price <= 0:
                                raise ValueError("Price must be greater than 0")
                        except (InvalidOperation, TypeError):
                            raise ValueError(f"Invalid price format: {product_data['price']}")

                        # ===== 4. HANDLE IMAGES =====
                        base_image_path = None
                        if product_data.get('base_image'):
                            image_path = os.path.join(
                                settings.MEDIA_ROOT,
                                'products/base',
                                product_data['base_image']
                            )
                            if os.path.exists(image_path):
                                base_image_path = f"products/base/{product_data['base_image']}"
                            else:
                                messages.warning(
                                    request,
                                    f"Row {idx}: Base image not found - {product_data['base_image']}"
                                )

                        # ===== 5. CREATE PRODUCT =====
                        product = Product.objects.create(
                            name=product_data['name'],
                            description=product_data['description'],
                            price=price,
                            subcategory_id_id=subcategory_id,
                            brand_id_id=brand_id,
                            material_id_id=material_id,
                            color=product_data['color'],
                            gender=product_data['gender'],
                            sku=product_data['sku'],
                            weight=product_data.get('weight'),
                            dimensions=product_data.get('dimensions'),
                            base_image=base_image_path
                        )

                        # ===== 6. HANDLE VARIANTS =====
                        variant_errors = []
                        for v_idx, variant in enumerate(product_data.get('variants', []), start=1):
                            try:
                                size_name = variant.get('size', '').lower()
                                size_id = ref_data['sizes'].get(size_name)
                                if not size_id:
                                    raise ValueError(f"Size '{variant.get('size')}' not found")

                                Product_Variants.objects.create(
                                    product_id=product,
                                    size_id_id=size_id,
                                    sku=variant.get('sku', f"{product_data['sku']}-{size_name.upper()}"),
                                    stock_quantity=int(variant.get('stock_quantity', 0)),
                                    additional_price=Decimal(str(variant.get('additional_price', 0))))
                            except Exception as e:
                                variant_errors.append(f"Variant {v_idx}: {str(e)}")

                        if variant_errors:
                            messages.warning(
                                request,
                                f"Row {idx}: {product_data['sku']} - "
                                f"{len(variant_errors)} variant(s) skipped: {', '.join(variant_errors)}"
                            )

                        # ===== 7. HANDLE GALLERY IMAGES =====
                        gallery_errors = []
                        for g_idx, gallery_item in enumerate(product_data.get('gallery', []), start=1):
                            try:
                                gallery_path = os.path.join(
                                    settings.MEDIA_ROOT,
                                    'products/gallery',
                                    gallery_item['image_path']
                                )
                                if os.path.exists(gallery_path):
                                    Product_Gallery.objects.create(
                                        product_id=product,
                                        image_path=f"products/gallery/{gallery_item['image_path']}",
                                        image_order=gallery_item.get('image_order', g_idx)
                                    )
                                else:
                                    raise ValueError(f"Image not found: {gallery_item['image_path']}")
                            except Exception as e:
                                gallery_errors.append(f"Gallery {g_idx}: {str(e)}")

                        if gallery_errors:
                            messages.warning(
                                request,
                                f"Row {idx}: {product_data['sku']} - "
                                f"{len(gallery_errors)} gallery image(s) skipped: {', '.join(gallery_errors)}"
                            )

                        success_count += 1

                    except Exception as e:
                        skipped_products.append(
                            f"Row {idx}: SKU {product_data.get('sku', '?')} - {str(e)}"
                        )
                        continue

                # Final report
                if success_count:
                    messages.success(
                        request,
                        f"Successfully imported {success_count}/{len(data['products'])} products"
                    )
                if skipped_products:
                    messages.warning(
                        request,
                        f"Skipped {len(skipped_products)} products: " +
                        "; ".join(skipped_products[:5]) + 
                        ("..." if len(skipped_products) > 5 else "")
                    )

                return redirect('display_product')

            except json.JSONDecodeError:
                messages.error(request, "Invalid JSON file format")
            except Exception as e:
                messages.error(request, f"File processing failed: {str(e)}")
            return redirect('add_product')

        # Handle regular form submission (non-JSON)
        else:
            try:
                subcategory = get_object_or_404(Sub_Category, id=request.POST.get('subcategory_id'))
                brand = get_object_or_404(Brand, id=request.POST.get('brand_id'))
                material = get_object_or_404(Material, id=request.POST.get('material_id'))
                # Create product with instances
                product = Product.objects.create(
                    name=request.POST.get('name'),
                    description=request.POST.get('description'),
                    price=request.POST.get('price'),
                    subcategory_id=subcategory, 
                    brand_id=brand,
                    material_id=material,
                    color=request.POST.get('color'),
                    gender=request.POST.get('gender'),
                    sku=request.POST.get('sku'),
                    weight=request.POST.get('weight'),
                    dimensions=request.POST.get('dimensions'),
                    base_image=request.FILES.get('base_image')
                )
                product.save()
                messages.success(request, 'Product added successfully!')
                return redirect('display_product')
            
            except Exception as e:
                messages.error(request, f'Error adding product: {str(e)}')
    
    # Get all categories, brands, and materials for the form
    categories = Category.objects.prefetch_related('subcategories').all()
    brands = Brand.objects.all()
    materials = Material.objects.all()
    
    context = {
        'categories': categories,
        'brands': brands,
        'materials': materials,
        'title': 'Add Product'
    }
    return render(request, 'add_product.html', context)

@admin_login_required
def display_product(request):
    # Get all active products with their variant counts
    products = Product.objects.filter(is_active=True).annotate(
        variant_count=models.Count('variants')
    ).order_by('name')
    
    return render(request, 'display_product.html', {
        'products': products
    })

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
            product.brand_id = brand
            product.material_id = material
            product.color = request.POST.get('color')
            product.gender = request.POST.get('gender')
            product.sku = request.POST.get('sku')
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
        messages.success(request, 'Product deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting product: {str(e)}')
    
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
        messages.success(request, "Variant deleted successfully!")
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

def display_orders(request):
    return render(request, 'display_orders.html')

def display_orderdetails(request):
    return render(request, 'display_orderdetails.html')

def display_cart(request):
    return render(request, 'display_cart.html')

def display_wishlist(request):
    return render(request, 'display_wishlist.html')

def display_payment(request):
    return render(request, 'display_payment.html')

def report_FBT(request):
    return render(request, 'report_FBT.html')

def report_customer(request):
    return render(request, 'report_customer.html')

def report_sales(request):
    return render(request, 'report_sales.html')