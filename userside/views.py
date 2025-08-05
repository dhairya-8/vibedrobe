import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login
from .decorators import user_login_required
from django.contrib import messages
from django.utils import timezone
from adminside.models import *
from django.core.paginator import Paginator
from django.db.models import Min, Max, Count, Avg, Prefetch
from django.db import IntegrityError
from django.views.decorators.http import require_POST
from .utils import *


def homepage(request):
   return render(request, 'homepage.html')

def login_register_view(request):
    """Handle both login and registration in one view"""
    active_tab = request.GET.get('tab', 'login')
    
    # Handle login form submission
    if request.method == 'POST' and 'login_email' in request.POST:
        email = request.POST.get('login_email')
        password = request.POST.get('login_password')
        remember_me = request.POST.get('remember', 'off') == 'on'
        
        try:
            user = User.objects.get(email=email)
            
            # Check if account is deactivated
            if not user.is_active:
                messages.error(request, 'Account is deactivated. Please contact support to reactivate.')
                return render(request, 'register.html', {
                    'login_form_data': {'email': email},
                    'active_tab': 'login'
                })
            
            if user.check_password(password):
                # Check again in case the account was deactivated between query and login
                if not user.is_active:
                    messages.error(request, 'Account is currently deactivated')
                    return redirect('login_register')
                
                # Set session data
                request.session['user_id'] = user.id
                request.session['user_email'] = user.email
                request.session['user_name'] = user.username
                
                # Remember me functionality
                request.session.set_expiry(1209600 if remember_me else 0)
                
                # Use Django's login() for session management
                auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                messages.success(request, 'Login successful!')
                return redirect('homepage')
            else:
                messages.error(request, 'Incorrect password')
        except User.DoesNotExist:
            messages.error(request, 'Email not registered')
        
        return render(request, 'register.html', {
            'login_form_data': {'email': email},
            'active_tab': 'login'
        })
    
    # Handle registration form submission (existing code remains same)
    elif request.method == 'POST' and 'register_email' in request.POST:
        form_data = {
            'username': request.POST.get('register_username'),
            'email': request.POST.get('register_email'),
            'password': request.POST.get('register_password'),
            'first_name': request.POST.get('first_name'),
        }
        
        errors = validate_user_data(form_data)
        
        if not errors:
            try:
                # Create user with minimal fields
                user = User.objects.create(
                    email=form_data['email'],
                    username=form_data['username'],
                    first_name=form_data['first_name'],
                    is_active=True,  # Ensure new accounts are active
                    # Other fields will use their defaults
                )
                user.set_password(form_data['password'])
                user.save()
                
                # Auto-login after registration
                request.session['user_id'] = user.id
                request.session['user_email'] = user.email
                request.session['user_name'] = user.first_name
                auth_login(request, user)
                
                messages.success(request, 'Registration successful! Please complete your profile.')
                success(f"Welcome {user.first_name}!", detailed=True)
                return redirect('profile')
                
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
                print(f"Registration error: {str(e)}")
        else:
            for field, error in errors.items():
                messages.error(request, f"{field}: {error}")
        
        return render(request, 'register.html', {
            'register_errors': errors,
            'register_form_data': form_data,
            'active_tab': 'register',
        })
    
    # GET request
    return render(request, 'register.html', {'active_tab': active_tab})

def validate_user_data(form_data):
    """Validate only the 4 required fields during registration"""
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
    """Logout clears session and uses Django's logout"""
    from django.contrib.auth import logout as auth_logout
    auth_logout(request)
    request.session.flush()
    messages.success(request, 'You have been logged out')
    return redirect('homepage')


# ============================= Account Views =============================
@user_login_required
def account_dashboard(request):
    """Render the account dashboard"""
    if 'user_id' not in request.session:
        messages.error(request, 'You need to log in first')
        return redirect('login_register_view')
    else:
        user_id = request.session['user_id']
        user = User.objects.get(id=user_id)
        return render(request, 'account_dashboard.html', {'user': user})

@user_login_required    
def account_orders(request):
    try:
        user_id_session = request.session.get('user_id')
        info(f'User ID: {user_id_session}')
        
        if not user_id_session:
            error('No session found')
            messages.error(request, 'Your session expired. Please login again.')
            return redirect('login')
            
        orders = Order_Master.objects.filter(user_id=user_id_session).order_by('-order_date')
        success(f'Found {orders.count()} orders')
        
        order_list = []
        for order in orders:
            order_list.append({
                'order': order,
                'item_count': order.order_details_set.count()
            })
        
        return render(request, 'account_orders.html', {'order_list': order_list})
        
    except Exception as e:
        error(f'Error: {str(e)}', detailed=True)
        messages.error(request, 'We encountered an error loading your orders.')
        return render(request, 'account_orders.html', {'order_list': []})

@user_login_required
def order_detail(request, order_id):
    try:
        user_id_session = request.session.get('user_id')
        info(f'Loading order {order_id} for user {user_id_session}')
        
        if not user_id_session:
            error('Session expired during modal load')
            messages.error(request, 'Your session expired. Please refresh the page.')
            return redirect('account_orders')
            
        order = Order_Master.objects.get(id=order_id, user_id=user_id_session)
        success(f"""Order #{order.order_number}
            Status: {order.status}
            Total: ₹{order.total_amount}
            Items: {order.order_details_set.count()}""", detailed=True)
        
        context = {
            'order': order,
            'order_items': order.order_details_set.all(),
            'shipping_address': order.order_address_set.filter(address_type='shipping').first(),
            'payment': order.payment_set.first(),
            'shipping': order.shipping_set.first(),
        }
        return render(request, 'account_order_detail_modal.html', context)
        
    except Order_Master.DoesNotExist:
        error(f'Order {order_id} not found')
        messages.error(request, 'The requested order was not found.')
        return redirect('account_orders')
        
    except Exception as e:
        error(f'Modal error: {str(e)}', detailed=True)
        messages.error(request, 'Failed to load order details. Please try again.')
        return redirect('account_orders')

@user_login_required
def account_addresses(request):
    
    user_id_from_session = request.session.get('user_id')
    addresses = User_Address.objects.filter(user_id=user_id_from_session).order_by('-is_default', '-updated_at')
    default_address = addresses.filter(is_default=True).first()
    
    context = {
        'addresses': addresses,
        'default_address': default_address,
    }
    return render(request, 'account_addresses.html', context)

@user_login_required
def add_address(request):
    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            
            address = User_Address(
                user_id_id=user_id,
                address_type=request.POST.get('address_type'),
                address_name=request.POST.get('address_name'),
                full_name=request.POST.get('full_name'),
                phone=request.POST.get('phone'),
                address_line_1=request.POST.get('address_line_1'),
                address_line_2=request.POST.get('address_line_2', ''),
                city=request.POST.get('city'),
                state=request.POST.get('state'),
                pincode=request.POST.get('pincode'),
                is_default=request.POST.get('is_default') == 'on'
            )
            
            if address.is_default:
                User_Address.objects.filter(user_id_id=user_id).update(is_default=False)
            
            address.save()
            messages.success(request, 'Address added successfully!')
            return redirect('account_addresses')
            
        except Exception as e:
            messages.error(request, f'Error adding address: {str(e)}')
    
    return render(request, 'account_add_address.html')

@user_login_required
def edit_address(request, address_id):
    user_id = request.session['user_id']
    address = get_object_or_404(User_Address, id=address_id, user_id_id=user_id)
    
    if request.method == 'POST':
        try:
            address.address_type = request.POST.get('address_type')
            address.address_name = request.POST.get('address_name')
            address.full_name = request.POST.get('full_name')
            address.phone = request.POST.get('phone')
            address.address_line_1 = request.POST.get('address_line_1')
            address.address_line_2 = request.POST.get('address_line_2', '')
            address.city = request.POST.get('city')
            address.state = request.POST.get('state')
            address.pincode = request.POST.get('pincode')
            
            new_default = request.POST.get('is_default') == 'on'
            if new_default and not address.is_default:
                User_Address.objects.filter(user_id_id=user_id).update(is_default=False)
                address.is_default = True
            elif not new_default and address.is_default:
                address.is_default = False
            
            address.save()
            messages.success(request, 'Address updated successfully!')
            return redirect('account_addresses')
        
        except Exception as e:
            messages.error(request, f'Error updating address: {str(e)}')
    
    return render(request, 'account_edit_address.html', {'address': address})

@user_login_required
def delete_address(request, address_id):
    user_id = request.session['user_id']
    address = get_object_or_404(User_Address, id=address_id, user_id_id=user_id)
    
    if address.is_default:
        messages.error(request, 'Cannot delete default address. Set another address as default first.')
    else:
        address.delete()
        messages.success(request, 'Address deleted successfully!')
    
    return redirect('account_addresses')

@user_login_required
def set_default_address(request, address_id):
    user_id = request.session['user_id']
    address = get_object_or_404(User_Address, id=address_id, user_id_id=user_id)
    
    if not address.is_default:
        User_Address.objects.filter(user_id_id=user_id).update(is_default=False)
        address.is_default = True
        address.save()
        messages.success(request, 'Default address updated!')
    else:
        messages.info(request, 'This address is already your default')
    
    return redirect('account_addresses')

@user_login_required
def account_details(request):
    if request.method == 'POST':
        if request.POST.get('form_type') == 'profile':
            # Handle profile update
            user = request.user
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            user.contact = request.POST.get('contact')
            user.date_of_birth = request.POST.get('date_of_birth')
            user.gender = request.POST.get('gender')
            
            if 'profile_image' in request.FILES:
                user.profile_image = request.FILES['profile_image']
            
            user.save()
            messages.success(request, 'Profile updated successfully!')
            
        elif request.POST.get('form_type') == 'password':
            # Handle password change
            current_password = request.POST.get('current_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')
            
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect')
            elif new_password1 != new_password2:
                messages.error(request, 'New passwords do not match')
            elif len(new_password1) < 8:
                messages.error(request, 'Password must be at least 8 characters')
            else:
                request.user.set_password(new_password1)
                request.user.save()
                
                # Re-login the user to maintain session
                from django.contrib.auth import login
                login(request, request.user)
                
                messages.success(request, 'Password changed successfully!')
                return redirect('account_details')
        
        return redirect('account_details')
    
    return render(request, 'account_details.html')

@user_login_required
def deactivate_account(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        if request.user.check_password(password):
            request.user.is_active = False
            request.user.save()
            
            from django.contrib.auth import logout
            logout(request)
            
            messages.success(request, 'Account deactivated successfully')
            return redirect('homepage')
        else:
            messages.error(request, 'Incorrect password')
            return redirect('account_details')
    return redirect('account_details')


# ============================= Shop Views =============================
def shop(request):
    # Get filter parameters
    category_id = request.GET.get('category')
    subcategory_id = request.GET.get('subcategory')
    size_ids = request.GET.getlist('size')
    brand_ids = request.GET.getlist('brand')
    sort = request.GET.get('sort', 'default')
    gender = request.GET.get('gender', None)

    # Base queryset
    products = Product.objects.filter(is_active=True).prefetch_related(
        Prefetch(
            'product_gallery_set',
            queryset=Product_Gallery.objects.order_by('image_order'),
            to_attr='ordered_gallery_images')
    ).select_related(
        'subcategory_id',
        'brand_id'
    )
    
     #gender
    if gender:
        products = products.filter(gender=gender)
        
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
        'current_gender': gender,
    }
    return render(request, 'shop.html', context)

def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related('subcategory_id', 'brand_id', 'material_id'),
        id=product_id,
        is_active=True
    )
    
    # Initialize has_purchased with default value
    has_purchased = False
    recently_viewed_products = []
    
    # Get all active variants with size information
    variants = Product_Variants.objects.filter(
        product_id=product,
        is_active=True
    ).select_related('size_id').order_by('size_id__name')
    
    # Check stock status at product level (sum of all variants)
    total_stock = sum(variant.stock_quantity for variant in variants)
    in_stock = total_stock > 0
    
    # Get gallery images ordered by image_order
    gallery_images = Product_Gallery.objects.filter(
        product_id=product
    ).order_by('image_order')
    
    # Get product tags
    tags = Product_Tags.objects.filter(product_id=product)
    
    # Get reviews with proper user instances
    reviews = Review.objects.filter(
        product_id=product
    ).select_related('user_id').order_by('-created_at')
    
    # Calculate average rating
    rating_agg = reviews.aggregate(
        average=Avg('rating'),
        count=Count('id')
    )
    average_rating = round(rating_agg['average'] or 0)
    rating_counts = {i: reviews.filter(rating=i).count() for i in range(5, 0, -1)}
    
    # Get related products (same subcategory and gender) excluding current product
    related_products = Product.objects.filter(
        subcategory_id=product.subcategory_id,
        gender=product.gender
    ).exclude(id=product.id).order_by('?')[:8]
    
    # Track recently viewed for authenticated users
    if request.user.is_authenticated:
        RecentlyViewed.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={'viewed_at': timezone.now()}
        )
        recently_viewed = RecentlyViewed.objects.filter(
            user=request.user
        ).exclude(product=product).order_by('-viewed_at')[:4]
        recently_viewed_products = [rv.product for rv in recently_viewed]
        
        # Check if user has purchased this product
        has_purchased = Order_Details.objects.filter(
            order_id__user_id=request.user,
            product_variant_id__product_id=product
        ).exists()
    
    context = {
        'product': product,
        'variants': variants,
        'in_stock': in_stock,
        'total_stock': total_stock,
        'gallery_images': gallery_images,
        'tags': tags,
        'reviews': reviews,
        'average_rating': average_rating,
        'rating_counts': rating_counts,
        'related_products': related_products,
        'recently_viewed_products': recently_viewed_products,
        'has_purchased': has_purchased,
    }
    
    return render(request, 'product_detail.html', context)

@require_POST
def check_variant_stock(request, variant_id):
    variant = get_object_or_404(Product_Variants, id=variant_id)
    return ({
        'in_stock': variant.stock_quantity > 0,
        'stock': variant.stock_quantity,
        'price': float(variant.product_id.price + variant.additional_price),
    })


# ========================= Single Add to Cart/Wihslist and Quick-view =========================
@user_login_required
def add_to_cart(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        variant = product.variants.filter(is_active=True).first()
        
        if not variant:
            messages.error(request, "This product is currently unavailable.")
            return redirect('shop')
        
        if variant.stock_quantity <= 0:
            messages.warning(request, f"Sorry, {product.name} is out of stock.")
            return redirect('shop')
        
        # Get or create user's cart
        cart, created = Cart.objects.get_or_create(user_id=request.user)
        
        # Check if item already exists in cart
        cart_item, created = Cart_Items.objects.get_or_create(
            cart_id=cart,
            product_variant_id=variant,
            defaults={
                'price_at_time': product.price + (variant.additional_price or 0),
                'quantity': 1
            }
        )
        
        if not created:
            # If item exists and we can add more
            new_quantity = cart_item.quantity + 1
            if new_quantity <= variant.stock_quantity:
                cart_item.quantity = new_quantity
                cart_item.save()
                messages.success(request, f"Added one more {product.name} to your cart. Total: {new_quantity}")
            else:
                messages.warning(request, 
                    f"You already have {cart_item.quantity} in cart. Only {variant.stock_quantity} available.")
        else:
            messages.success(request, f"✓ {product.name} added to cart!")
        
    except Exception as e:
        messages.error(request, "Couldn't add item to cart. Please try again.")
        # Log the error here in production
    
    return redirect('shop')


@user_login_required
def add_to_wishlist(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # Check if product is already in wishlist
        if Wishlist.objects.filter(user_id=request.user, product_id=product).exists():
            messages.info(request, f"{product.name} is already in your wishlist 💖")
        else:
            Wishlist.objects.create(user_id=request.user, product_id=product)
            messages.success(request, f"✓ {product.name} added to wishlist!")
            
    except IntegrityError:
        messages.error(request, "Couldn't add to wishlist. Please try again.")
    except Exception as e:
        messages.error(request, "An unexpected error occurred.")
        # Log the error here in production
    
    return redirect('shop')

# ========================= Static Pages =========================
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