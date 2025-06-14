from django.shortcuts import render, redirect
from django.contrib import messages
from .models import *
from .decorators import admin_login_required

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
      request.session.flush()
      print("Admin logout successfully !")
      messages.success(request, 'You have been successfully logged out.')
      return redirect('login')
 
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
            return redirect('display_subcategories')
            
        return render(request, 'edit_subcategory.html', {
            'subcategory': subcategory,
            'categories': categories
        })
    
    except Sub_Category.DoesNotExist:
        messages.error(request, "SubCategory not found")
        return redirect('display_subcategories')
    except Category.DoesNotExist:
        messages.error(request, "Invalid category selected")
        return redirect('display_subcategories')

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
    return redirect('display_subcategories')

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
            brand.save()
            messages.success(request, "Brand updated successfully!")
            return redirect('display_brands')
            
        return render(request, 'edit_brand.html', {'brand': brand})
    
    except Brand.DoesNotExist:
        messages.error(request, "Brand not found")
        return redirect('display_brands')

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
    return redirect('display_brands')
 
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
            size.save()
            messages.success(request, "Size updated successfully!")
            return redirect('display_sizes')
            
        return render(request, 'edit_size.html', {'size': size})
    
    except Size.DoesNotExist:
        messages.error(request, "Size not found")
        return redirect('display_sizes')

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
    return redirect('display_sizes')
 
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
            material.save()
            messages.success(request, "Material updated successfully!")
            return redirect('display_materials')
            
        return render(request, 'edit_material.html', {'material': material})
    
    except Material.DoesNotExist:
        messages.error(request, "Material not found")
        return redirect('display_materials')

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
    return redirect('display_materials')

# Product Views
@admin_login_required
def add_product(request):
    if request.method == 'POST':
        try:
            product = Product.objects.create(
                name=request.POST.get('name', '').strip(),
                description=request.POST.get('description', '').strip(),
                price=request.POST.get('price', 0),
                base_image=request.POST.get('base_image', '').strip(),
                subcategory_id=Sub_Category.objects.get(id=request.POST.get('subcategory_id')),
                brand_id=Brand.objects.get(id=request.POST.get('brand_id')),
                color=request.POST.get('color', '').strip(),
                material_id=Material.objects.get(id=request.POST.get('material_id')),
                gender=request.POST.get('gender', '').strip(),
                sku=request.POST.get('sku', '').strip(),
                weight=request.POST.get('weight'),
                dimensions=request.POST.get('dimensions', '').strip(),
                is_active=True
            )
            messages.success(request, "Product added successfully!")
            return redirect('add_product_variants', product_id=product.id)
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('add_product')
    
    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    materials = Material.objects.filter(is_active=True)
    return render(request, 'add_product.html', {
        'categories': categories,
        'brands': brands,
        'materials': materials
    })

@admin_login_required
def edit_product(request, id):
    try:
        product = Product.objects.get(id=id)
        
        if request.method == 'POST':
            product.name = request.POST.get('name', '').strip()
            product.description = request.POST.get('description', '').strip()
            product.price = request.POST.get('price', 0)
            product.base_image = request.POST.get('base_image', '').strip()
            product.subcategory_id = Sub_Category.objects.get(id=request.POST.get('subcategory_id'))
            product.brand_id = Brand.objects.get(id=request.POST.get('brand_id'))
            product.color = request.POST.get('color', '').strip()
            product.material_id = Material.objects.get(id=request.POST.get('material_id'))
            product.gender = request.POST.get('gender', '').strip()
            product.sku = request.POST.get('sku', '').strip()
            product.weight = request.POST.get('weight')
            product.dimensions = request.POST.get('dimensions', '').strip()
            product.save()
            
            messages.success(request, "Product updated successfully!")
            return redirect('display_products')
            
        categories = Category.objects.filter(is_active=True)
        brands = Brand.objects.filter(is_active=True)
        materials = Material.objects.filter(is_active=True)
        subcategories = Sub_Category.objects.filter(category_id=product.subcategory_id.category_id)
        
        return render(request, 'edit_product.html', {
            'product': product,
            'categories': categories,
            'subcategories': subcategories,
            'brands': brands,
            'materials': materials
        })
    
    except Product.DoesNotExist:
        messages.error(request, "Product not found")
        return redirect('display_products')
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('display_products')

@admin_login_required
def display_product(request):
    products = Product.objects.select_related(
        'subcategory_id', 
        'brand_id', 
        'material_id'
    ).all()
    return render(request, 'display_products.html', {'products': products})

@admin_login_required
def delete_product(request, id):
    try:
        product = Product.objects.get(id=id)
        product.delete()
        messages.success(request, "Product deleted successfully!")
    except Product.DoesNotExist:
        messages.error(request, "Product not found")
    return redirect('display_product')
 
# Product Variant Views
@admin_login_required
def add_product_variants(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        
        if request.method == 'POST':
            Product_Variants.objects.create(
                product_id=product,
                size_id=Size.objects.get(id=request.POST.get('size_id')),
                sku=request.POST.get('sku', '').strip(),
                stock_quantity=request.POST.get('stock_quantity', 0),
                reserved_quantity=request.POST.get('reserved_quantity', 0),
                additional_price=request.POST.get('additional_price', 0),
                is_active=True
            )
            messages.success(request, "Variant added successfully!")
            return redirect('add_product_variants', product_id=product_id)
        
        sizes = Size.objects.filter(is_active=True)
        variants = Product_Variants.objects.filter(product_id=product)
        return render(request, 'add_product_variants.html', {
            'product': product,
            'sizes': sizes,
            'variants': variants
        })
    
    except Product.DoesNotExist:
        messages.error(request, "Product not found")
        return redirect('display_product')

@admin_login_required
def edit_product_variant(request, id):
    try:
        variant = Product_Variants.objects.get(id=id)
        
        if request.method == 'POST':
            variant.size_id = Size.objects.get(id=request.POST.get('size_id'))
            variant.sku = request.POST.get('sku', '').strip()
            variant.stock_quantity = request.POST.get('stock_quantity', 0)
            variant.reserved_quantity = request.POST.get('reserved_quantity', 0)
            variant.additional_price = request.POST.get('additional_price', 0)
            variant.save()
            
            messages.success(request, "Variant updated successfully!")
            return redirect('add_product_variants', product_id=variant.product_id.id)
            
        sizes = Size.objects.filter(is_active=True)
        return render(request, 'edit_product_variant.html', {
            'variant': variant,
            'sizes': sizes
        })
    
    except Product_Variants.DoesNotExist:
        messages.error(request, "Variant not found")
        return redirect('display_products')

@admin_login_required
def delete_product_variant(request, id):
    try:
        variant = Product_Variants.objects.get(id=id)
        product_id = variant.product_id.id
        variant.delete()
        messages.success(request, "Variant deleted successfully!")
        return redirect('add_product_variants', product_id=product_id)
    except Product_Variants.DoesNotExist:
        messages.error(request, "Variant not found")
        return redirect('display_products')
    
def display_admin(request):
    return render(request, 'display_admin.html')

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