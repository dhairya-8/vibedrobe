import re
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.utils import timezone
from adminside.models import *
from django.shortcuts import render, get_object_or_404
from adminside.models import *
from django.core.paginator import Paginator
from django.db.models import Min, Max, Count
from django.http import JsonResponse


def homepage(request):
   return render(request, 'homepage.html')

def login_register_view(request):
    """Handle both login and registration in one view"""
    # Handle login form submission
    if request.method == 'POST' and 'login_email' in request.POST:
        email = request.POST.get('login_email')
        password = request.POST.get('login_password')
        remember_me = request.POST.get('remember', 'off') == 'on'
        
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                # Set session data
                request.session['user_id'] = user.id
                request.session['user_email'] = user.email
                request.session['user_name'] = user.first_name
                print(f"User logged in: {user.username} ({user.email})")
                
                # Update last login
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                
                # Remember me functionality
                request.session.set_expiry(1209600 if remember_me else 0)
                
                messages.success(request, 'Login successful!')
                return redirect('homepage')
            else:
                messages.info(request, 'Incorrect password')
        except User.DoesNotExist:
            messages.error(request, 'Email not registered')
        
        return render(request, 'register.html', {
            'login_form_data': {'email': email},
            'active_tab': 'login'
        })
    
    # Handle registration form submission (only 4 required fields now)
    elif request.method == 'POST' and 'register_email' in request.POST:
        form_data = {
            'username': request.POST.get('register_username'),
            'email': request.POST.get('register_email'),
            'password': request.POST.get('register_password'),
            'first_name': request.POST.get('first_name'),
        }
        
        errors = {}
        
        # Validate username
        if not form_data['username']:
            errors['username'] = 'Username is required'
        elif len(form_data['username']) < 4:
            errors['username'] = 'Username must be at least 4 characters'
        elif User.objects.filter(username=form_data['username']).exists():
            errors['username'] = 'Username already taken'
        
        # Validate email
        if not form_data['email']:
            errors['email'] = 'Email is required'
        elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', form_data['email']):
            errors['email'] = 'Enter a valid email address'
        elif User.objects.filter(email=form_data['email']).exists():
            errors['email'] = 'Email already registered'
        
        # Validate password
        if not form_data['password']:
            errors['password'] = 'Password is required'
        elif len(form_data['password']) < 8:
            errors['password'] = 'Password must be at least 8 characters'
        
        # Validate first name
        if not form_data['first_name']:
            errors['first_name'] = 'First name is required'
        
        if not errors:
            try:
                # Create user with minimal fields first
                user = User.objects.create(
                    username=form_data['username'],
                    email=form_data['email'],
                    first_name=form_data['first_name'],
                    is_active=True,
                    is_verified=True,
                    registration_date=timezone.now().date(),
                    # Set default values for required fields
                    last_name='',  # Can be updated later
                    contact=0,     # Can be updated later
                    date_of_birth=timezone.now().date(),  # Can be updated later
                    gender='1'     # Can be updated later
                )
                # Set password properly
                user.set_password(form_data['password'])
                user.save()
                
                # Auto-login after registration
                auth_user = authenticate(request, email=form_data['email'], password=form_data['password'])
                if auth_user:
                    login(request, auth_user)
                    request.session['user_id'] = user.id
                    request.session['user_email'] = user.email
                    request.session['user_name'] = user.first_name
                
                messages.success(request, 'Registration successful! Please complete your profile.')
                return redirect('profile')
                
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
                # Print the error for debugging
                print(f"Registration error: {str(e)}")
        else:
            for field, error in errors.items():
                messages.error(request, f"{field}: {error}")
        
        return render(request, 'register.html', {
            'register_errors': errors,
            'register_form_data': form_data,
            'active_tab': 'register'
        })
    
    # GET request - show form
    return render(request, 'register.html')

def validate_user_data(form_data):
    """Validate only the 4 required fields"""
    errors = {}
    
    # Username validation
    if not form_data['username']:
        errors['username'] = 'Username is required'
    elif len(form_data['username']) < 4:
        errors['username'] = 'Username must be at least 4 characters'
    elif User.objects.filter(username=form_data['username']).exists():
        errors['username'] = 'Username already taken'
    
    # Email validation
    if not form_data['email']:
        errors['email'] = 'Email is required'
    elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', form_data['email']):
        errors['email'] = 'Enter a valid email address'
    elif User.objects.filter(email=form_data['email']).exists():
        errors['email'] = 'Email already registered'
    
    # Password validation
    if not form_data['password']:
        errors['password'] = 'Password is required'
    elif len(form_data['password']) < 8:
        errors['password'] = 'Password must be at least 8 characters'
    
    # First name validation
    if not form_data['first_name']:
        errors['first_name'] = 'First name is required'
    
    return errors

def user_logout(request):
    """Handle user logout"""
    request.session.flush()
    print("User logged out")
    messages.success(request, 'You have been logged out')
    return redirect('homepage')

def account_dashboard(request):
    """Render the account dashboard"""
    if 'user_id' not in request.session:
        messages.error(request, 'You need to log in first')
        return redirect('login_register_view')
    else:
        user_id = request.session['user_id']
        user = User.objects.get(id=user_id)
        return render(request, 'account_dashboard.html', {'user': user})

def shop(request):
    # Get filter parameters
    category_id = request.GET.get('category')
    subcategory_id = request.GET.get('subcategory')
    size_ids = request.GET.getlist('size')
    brand_ids = request.GET.getlist('brand')
    sort = request.GET.get('sort', 'default')
    
    # Base queryset
    products = Product.objects.filter(is_active=True).prefetch_related(
        'product_gallery_set'
    ).select_related(
        'subcategory_id',
        'brand_id'
    )
    
    # Apply filters
    if size_ids:
        products = products.filter(variants__size_id__in=size_ids).distinct()
    
    if brand_ids:
        products = products.filter(brand_id__in=brand_ids)
    
    if subcategory_id:
        products = products.filter(subcategory_id=subcategory_id)
    elif category_id:
        products = products.filter(subcategory_id__category_id=category_id)
    
    # Price filtering
    price_stats = products.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    global_min_price = price_stats['min_price'] or 0
    global_max_price = price_stats['max_price'] or 1000
    
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    try:
        min_price = float(min_price) if min_price else None
        max_price = float(max_price) if max_price else None
    except (TypeError, ValueError):
        min_price = None
        max_price = None
    
    if min_price is not None and max_price is not None:
        products = products.filter(price__gte=min_price, price__lte=max_price)
    elif min_price is not None:
        products = products.filter(price__gte=min_price)
    elif max_price is not None:
        products = products.filter(price__lte=max_price)
    
    # Sorting
    sort_options = {
        'price-low': 'price',
        'price-high': '-price',
        'a-z': 'name',
        'z-a': '-name',
        'date-new': '-created_at',
        'date-old': 'created_at',
        'default': 'id'
    }
    products = products.order_by(sort_options[sort])

    # Brands data
    all_brands = Brand.objects.filter(is_active=True).annotate(
        product_count=Count('product')
    ).order_by('name')

    # Get selected brand IDs
    selected_brand_ids = []
    for brand_id in request.GET.getlist('brand'):
        try:
            selected_brand_ids.append(int(brand_id))
        except (ValueError, TypeError):
            continue
    
    # Create ordered brands list (selected first)
    selected_brands = [b for b in all_brands if b.id in selected_brand_ids]
    unselected_brands = [b for b in all_brands if b.id not in selected_brand_ids]
    ordered_brands = selected_brands + unselected_brands

    # Prepare categories with subcategories
    categories_with_subcategories = []
    selected_subcategory = int(subcategory_id) if subcategory_id and subcategory_id.isdigit() else None
    
    for category in Category.objects.filter(is_active=True).prefetch_related('subcategories'):
        subcategory_ids = list(category.subcategories.all().values_list('id', flat=True))
        categories_with_subcategories.append({
            'category': category,
            'subcategory_ids': subcategory_ids,
            'has_selected_subcategory': selected_subcategory in subcategory_ids if selected_subcategory else False
        })

    # Pagination
    paginator = Paginator(products, 28)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'categories_with_subcategories': categories_with_subcategories,
        'sizes': Size.objects.filter(is_active=True).order_by('sort_order'),
        'brands': all_brands,
        'ordered_brands': ordered_brands,
        'selected_brands': selected_brand_ids,
        'selected_sizes': [int(size) for size in size_ids if size.isdigit()],
        'selected_subcategory': selected_subcategory,
        'products': page_obj,
        'sort': sort,
        'min_price': min_price,
        'max_price': max_price,
        'global_min_price': global_min_price,
        'global_max_price': global_max_price,
    }
    return render(request, 'shop.html', context)


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    variants = product.variants.filter(is_active=True)
    gallery_images = product.product_gallery_set.all().order_by('image_order')
    
    context = {
        'product': product,
        'variants': variants,
        'gallery_images': gallery_images,
    }
    return render(request, 'product_detail.html', context)

def add_to_cart(request, product_id):
    # Implement your cart logic here
    # This is just a placeholder
    product = get_object_or_404(Product, id=product_id)
    # Your cart addition logic would go here
    return JsonResponse({'status': 'success'})

def add_to_wishlist(request, product_id):
    # Implement your wishlist logic here
    # This is just a placeholder
    product = get_object_or_404(Product, id=product_id)
    # Your wishlist addition logic would go here
    return JsonResponse({'status': 'success'})


def contactus(request):
   return render(request, 'contactus.html')

def aboutus(request):
   return render(request, 'aboutus.html')

def orderconfirm(request):
   return render(request, 'orderconfirm.html')

def checkout(request):
   return render(request, 'checkout.html')

def forgotpassword(request):
   return render(request, 'forgotpassword.html')