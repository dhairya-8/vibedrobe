# Standard library
import re
import time
import random
import string
import os
import numpy as np
from decimal import Decimal

# Django core
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.mail import BadHeaderError, EmailMultiAlternatives, send_mail
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Min, Prefetch, Sum, Avg, Case, When, Value, IntegerField
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST

from django.core.files.storage import FileSystemStorage
from sklearn.metrics.pairwise import cosine_similarity
from adminside.management.commands.generate_features import extract_features # And command

# Project-level
from .decorators import user_login_required
from .utils import *
from adminside.models import *

# Third-party
import razorpay


# Get the User model
User = get_user_model()

# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))



# ============================= AUTHENTICATION VIEWS =============================


def homepage(request):
    """
    View for the homepage, fetching various product lists.
    """
    
    # Fetch New Arrivals (latest 8 products)
    # all_products = Product.objects.filter(is_active=True).order_by('id')[:8]
    
    # Fetch New Arrivals (latest 8 products)
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at')[:8]

    # Fetch Best Sellers (top 8 products by quantity sold)
    # This query calculates the sum of quantities sold for each product.
    best_seller_ids = Order_Details.objects.values('product_variant_id__product_id') \
        .annotate(total_sold=Sum('quantity')) \
        .order_by('-total_sold') \
        .values_list('product_variant_id__product_id', flat=True)
        
    # Fetch the product objects for the best seller IDs
    # Note: This creates a new query. For very large datasets, you might optimize.
    best_sellers = Product.objects.filter(id__in=list(best_seller_ids)[:8])

    # Fetch Top Rated products (top 8 by average rating)
    top_rated = Product.objects.filter(is_active=True) \
        .annotate(average_rating=Avg('review__rating')) \
        .filter(average_rating__isnull=False) \
        .order_by('-average_rating')[:8]

    # Fetch Limited Edition products (carousel)
    limited_edition = Product.objects.filter(product_tags__tag__iexact='Limited Edition', is_active=True)[:8]
    if not limited_edition.exists():
        # Fallback: get the 8 most expensive products if the tag doesn't exist or isn't used
        limited_edition = Product.objects.filter(is_active=True).order_by('-price')[:8]

    try:
        ethnic_category = Category.objects.get(name__iexact="Ethnic Wear")
    except Category.DoesNotExist:
        ethnic_category = None

    try:
        tshirts_subcategory = Sub_Category.objects.get(name__iexact="T-Shirts")
    except Sub_Category.DoesNotExist:
        tshirts_subcategory = None
        
    try:
        jackets_subcategory = Sub_Category.objects.get(name__iexact="Jacket")
    except Sub_Category.DoesNotExist:
        jackets_subcategory = None 
        
    # Calculate the minimum price for Women's T-Shirts
    tshirts_min_price = None
    if tshirts_subcategory:
        price_agg = Product.objects.filter(
            subcategory_id=tshirts_subcategory, 
            gender='Female'
        ).aggregate(min_price=Min('price'))
        tshirts_min_price = price_agg.get('min_price')

    # Calculate the minimum price for Men's Jackets
    jackets_min_price = None
    if jackets_subcategory:
        price_agg = Product.objects.filter(
            subcategory_id=jackets_subcategory, 
            gender='Male'
        ).aggregate(min_price=Min('price'))
        jackets_min_price = price_agg.get('min_price')
    
    context = {
        'all_products': new_arrivals, # Using new_arrivals for the 'All' tab for simplicity
        'new_arrivals': new_arrivals,
        'best_sellers': best_sellers,
        'top_rated': top_rated,
        'limited_edition_products': limited_edition,
        'ethnic_category': ethnic_category,
        'tshirts_subcategory': tshirts_subcategory,
        'jackets_subcategory': jackets_subcategory,
        'tshirts_min_price': tshirts_min_price,
        'jackets_min_price': jackets_min_price,
    }
    
    return render(request, 'homepage.html', context)

def login_register_view(request):
    """Handle both login and registration in one view"""
    active_tab = request.GET.get('tab', 'login')

    # -------------------------------
    # LOGIN LOGIC
    # -------------------------------
    if request.method == 'POST' and 'login_email' in request.POST:
        email = request.POST.get('login_email')
        password = request.POST.get('login_password')
        remember_me = request.POST.get('remember', 'off') == 'on'

        try:
            user = User.objects.get(email=email)

            if not user.is_active:
                messages.error(request, 'Account is deactivated. Please contact support.')
                return render(request, 'register.html', {
                    'login_form_data': {'email': email},
                    'active_tab': 'login'
                })

            if user.check_password(password):
                # update last login time
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])

                # Set user-specific session keys
                request.session['user_id'] = user.id
                request.session['user_email'] = user.email
                request.session['user_name'] = user.username

                # Remember me functionality
                request.session.set_expiry(1209600 if remember_me else 0)

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

    # -------------------------------
    # REGISTRATION LOGIC (Updated with Email)
    # -------------------------------
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
                user = User.objects.create(
                    email=form_data['email'],
                    username=form_data['username'],
                    first_name=form_data['first_name'],
                    is_active=True,
                )
                user.set_password(form_data['password'])
                user.save()

                # --- 📧 SEND WELCOME EMAIL ---
                try:
                    # Build the base URL directly from the request object
                    base_url = f"{request.scheme}://{request.get_host()}"

                    subject = 'Welcome to VibeDrobe! 🎉'
                    context = {
                        'user': user,
                        'base_url': base_url, # Pass the full base URL
                    }
                    html_message = render_to_string('emails/welcome_email.html', context)
                    plain_message = strip_tags(html_message)
                    from_email = settings.DEFAULT_FROM_EMAIL
                    to_email = user.email

                    send_mail(subject, plain_message, from_email, [to_email], html_message=html_message)
                except Exception as e:
                    # Log email sending error but don't crash registration
                    print(f"ERROR: Could not send welcome email to {user.email}. Reason: {e}")
                # --- END OF EMAIL LOGIC ---

                # auto-login after registration
                request.session['user_id'] = user.id
                request.session['user_email'] = user.email
                request.session['user_name'] = user.username
                request.session.set_expiry(0)  # default browser session

                # Updated success message
                messages.success(request, 'Registration successful! A welcome email has been sent to your inbox.')
                return redirect('account_details')

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

    # -------------------------------
    # GET request (Unchanged)
    # -------------------------------
    return render(request, 'register.html', {'active_tab': active_tab})

def user_logout(request):
    """Logout clears only user-specific session keys"""
    for key in ['user_id', 'user_email', 'user_name']:
        if key in request.session:
            del request.session[key]

    messages.success(request, 'You have been logged out')
    return redirect('homepage')

def forgotpassword(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            
            # Your original logic for token generation
            reset_token = ''.join(random.choices(string.ascii_letters + string.digits, k=50))
            
            # Your original logic for storing token in session
            request.session['reset_token'] = reset_token
            request.session['reset_email'] = email
            request.session.set_expiry(900)  # Token valid for 15 mins
            
            # Your original logic for creating the reset link
            reset_link = f"{request.scheme}://{request.get_host()}/reset-password/{reset_token}/"
            
            # --- START: Themed Email Sending Logic ---
            subject = 'Password Reset Request - VibeDrobe'
            context = {
                'user': user,
                'reset_link': reset_link,
            }
            # Renders the HTML template you created
            html_message = render_to_string('emails/password_reset_email.html', context)
            # Creates a plain text version for email clients that don't support HTML
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message, # Plain text version
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message # HTML version
            )
            # --- END: Themed Email Sending Logic ---
            
            messages.success(request, 'Password reset email sent. Please check your inbox.')
            return redirect('login_register')
            
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
    
    return render(request, 'forgotpassword.html')

def reset_password(request, token):
    # Check if token matches what's in the session
    if request.session.get('reset_token') != token:
        messages.error(request, 'Invalid or expired reset token.')
        return redirect('forgotpassword')
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
        elif len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
        else:
            email = request.session.get('reset_email')
            try:
                user = User.objects.get(email=email)
                user.set_password(new_password)
                user.save()
                
                # Clear the reset session data
                if 'reset_token' in request.session:
                    del request.session['reset_token']
                if 'reset_email' in request.session:
                    del request.session['reset_email']
                
                messages.success(request, 'Password reset successfully. You can now login with your new password.')
                return redirect('login_register')
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
    
    return render(request, 'reset_password.html', {'token': token})


# ============================= ACCOUNT MANAGEMENT VIEWS =============================


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
        
        if not user_id_session:
            error('No session found')
            messages.error(request, 'Your session expired. Please login again.')
            return redirect('login')
            
        orders = Order_Master.objects.filter(user_id=user_id_session).order_by('-order_date')
        
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
        
        if not user_id_session:
            error('Session expired during modal load')
            messages.error(request, 'Your session expired. Please refresh the page.')
            return redirect('account_orders')
            
        order = Order_Master.objects.get(id=order_id, user_id=user_id_session)
        payment = order.payment_set.first()
        # Auto-fail pending payments after 30 minutes
        if payment and hasattr(payment, 'fail_if_pending_timeout'):
            payment.fail_if_pending_timeout(minutes=15)

        order_address = Order_Address.objects.filter(order_id=order)
        
        context = {
            'order': order,
            'order_items': order.order_details_set.all(),
            'shipping_address': order_address.first(),
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
@require_POST
def cancel_order(request, order_id):
    try:
        user_id_session = request.session.get('user_id')
        order = get_object_or_404(Order_Master, id=order_id, user_id_id=user_id_session)

        if order.status in ['processing', 'confirmed']:
            # [IMPROVEMENT] Use a transaction to ensure data integrity
            with transaction.atomic():
                # --- Restock Inventory ---
                order_items = order.order_details_set.all()
                for item in order_items:
                    variant = item.product_variant_id
                    
                    # --- [FIX] Check if the variant still exists ---
                    if variant:
                        variant.stock_quantity += item.quantity
                        variant.save()
                    else:
                        # This variant was likely deleted. Log this serious issue.
                        error(f"Cannot restock item for Order #{order.order_number}. Product Variant ID {item.product_variant_id_id} not found.")
                        # We will still cancel the order but the admin needs to know about the stock discrepancy.
                
                # --- Handle Refund for Prepaid Orders ---
                if order.mode_of_payment != 'cod':
                    try:
                        payment = Payment.objects.get(order_id=order)
                        payment.status = 'refund_initiated'
                        payment.refund_amount = order.total_amount
                        payment.refund_reason = 'Order cancelled by customer.'
                        payment.save()
                    except Payment.DoesNotExist:
                        error(f'Payment record not found for prepaid order {order.order_number} during cancellation.')
                        
                # --- Update Order Status ---
                order.status = 'cancelled'
                order.save()
            
            messages.success(request, f"Order #{order.order_number} has been successfully cancelled.")

        else:
            messages.error(request, "This order cannot be cancelled as it has already been shipped.")

    except Exception as e:
        error(f'Error cancelling order: {str(e)}', detailed=True)
        messages.error(request, "An unexpected error occurred. Please try again.")

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
                phone = "+91" + request.POST.get('phone'),                
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
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Please login to continue")
        return redirect('login_register')

    try:
        user = User.objects.get(id=user_id)  # fetch from DB using session
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('homepage')

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'profile':
            # Profile update
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.contact = request.POST.get('contact', user.contact)
            user.date_of_birth = request.POST.get('date_of_birth', user.date_of_birth)
            user.gender = request.POST.get('gender', user.gender)

            if 'profile_image' in request.FILES:
                user.profile_image = request.FILES['profile_image']
                
            elif request.POST.get('clear_image') == '1':
                user.profile_image.delete(save=False)
                user.profile_image = None

            user.save()
            messages.success(request, 'Profile updated successfully!')

        elif form_type == 'password':
            # Password change
            current_password = request.POST.get('current_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            if not user.check_password(current_password):
                messages.error(request, 'Current password is incorrect')
            elif new_password1 != new_password2:
                messages.error(request, 'New passwords do not match')
            elif len(new_password1) < 8:
                messages.error(request, 'Password must be at least 8 characters')
            else:
                user.set_password(new_password1)
                user.save()
                messages.success(request, 'Password changed successfully!')
                return redirect('account_details')

        return redirect('account_details')

    return render(request, 'account_details.html', {"user": user})


@user_login_required
def deactivate_account(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        try:
            # get current user from session
            user_id = request.session.get('user_id')
            user = User.objects.get(id=user_id)

            if user.check_password(password):
                user.is_active = False
                user.save()

                # --- 📧 SEND DEACTIVATION CONFIRMATION EMAIL ---
                try:
                    subject = 'Your VibeDrobe Account Has Been Deactivated'
                    context = {'user': user}
                    html_message = render_to_string('emails/account_deactivated_email.html', context)
                    plain_message = strip_tags(html_message)
                    
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        html_message=html_message
                    )
                except Exception as e:
                    # Log email error, but don't stop the deactivation process
                    print(f"ERROR: Could not send deactivation email to {user.email}. Reason: {e}")
                # --- END OF EMAIL LOGIC ---

                # clear only user session keys
                for key in ['user_id', 'user_email', 'user_name']:
                    if key in request.session:
                        del request.session[key]

                messages.success(request, 'Account deactivated successfully. A confirmation email has been sent.')
                return redirect('homepage')
            else:
                messages.error(request, 'Incorrect password')
                return redirect('account_details')

        except User.DoesNotExist:
            messages.error(request, 'User not found. Please log in again.')
            return redirect('login_register')

    return redirect('account_details')


# ============================= PRODUCT VIEWS =============================
def image_search_view(request):
    if request.method == 'POST' and request.FILES.get('query_img'):
        SIMILARITY_THRESHOLD = 0.65 

        # --- 1. Perform the Search (same logic as prototype) ---
        query_img_file = request.FILES['query_img']
        fs = FileSystemStorage()
        query_path_relative = fs.save(query_img_file.name, query_img_file)
        query_path_full = fs.path(query_path_relative)
        query_features = np.array(extract_features(query_path_full))
        indexed_products = ML_Feature_Vectors.objects.select_related('product_id').all()

        all_matches = []
        for indexed_product in indexed_products:
            sim = cosine_similarity(
                query_features.reshape(1, -1), 
                np.array(indexed_product.feature_vector).reshape(1, -1)
            )[0][0]
            if sim >= SIMILARITY_THRESHOLD:
                all_matches.append((indexed_product.product_id, sim))

        all_matches.sort(key=lambda x: x[1], reverse=True)

        # --- 2. Get the IDs of the matching products ---
        product_ids = [product.id for product, sim in all_matches]

        if not product_ids:
            # Handle no results found, maybe redirect with a message
            return redirect(reverse('shop') + '?image_search_status=no_results')

        # --- 3. Redirect to the shop page with the IDs ---
        shop_url = reverse('shop')
        id_string = ','.join(map(str, product_ids))
        return redirect(f'{shop_url}?similar_to={id_string}')

    return render(request, 'image_search.html')


def shop(request):
    
    keyword = request.GET.get('search-keyword', None)    
    # Get filter parameters
    category_id = request.GET.get('category')
    subcategory_id = request.GET.get('subcategory')
    size_ids = request.GET.getlist('size')
    brand_ids = request.GET.getlist('brand')
    sort = request.GET.get('sort', 'default')
    gender = request.GET.get('gender', None)

    # --- NEW: Check for image search results ---
    similar_product_ids = request.GET.get('similar_to')
    image_search_status = request.GET.get('image_search_status')
    
    # Base queryset - ADD VARIANT PREFETCH HERE
    products = Product.objects.filter(is_active=True).prefetch_related(
        Prefetch(
            'product_gallery_set',
            queryset=Product_Gallery.objects.order_by('image_order'),
            to_attr='ordered_gallery_images'
        ),
        Prefetch(  # ADD THIS PREFETCH FOR VARIANTS
            'variants',
            queryset=Product_Variants.objects.select_related('size_id'),
            to_attr='variants_list'
        )
    ).select_related(
        'subcategory_id',
        'brand_id'
    )
    if similar_product_ids:
        # If we have IDs from an image search, filter by them
        product_id_list = [int(pid) for pid in similar_product_ids.split(',') if pid.isdigit()]
        products = products.filter(id__in=product_id_list)
        
    # STEP 2: Apply the search filter if a keyword exists
    if keyword:
        products = products.annotate(
            relevance=Case(
                When(name__icontains=keyword, then=Value(1)),
                When(subcategory_id__name__icontains=keyword, then=Value(2)),
                When(brand_id__name__icontains=keyword, then=Value(3)),
                When(description__icontains=keyword, then=Value(4)), # This still gets scored...
                default=Value(5),
                output_field=IntegerField()
            )
        # ...but this line now EXCLUDES it from the results.
        ).filter(relevance__lte=3).order_by('relevance')
        
    # gender
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
        'default': '-created_at'
    }
    
    # If a search is active, we sort by relevance first, then by the user's choice.
    if keyword:
        # For default sort on a search page, relevance is all we need.
        # For other sorts, we use relevance as the primary sorter.
        if sort != 'default':
             products = products.order_by('relevance', sort_options[sort])
    else:
        # Original sorting if no search is performed
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
        
        # STEP 3: Add the keyword to the context
        'keyword': keyword,
        
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
        'image_search_status': image_search_status,
    }
    return render(request, 'shop.html', context)


def new_arrivals(request):
    # Get new arrivals (products added in the last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    products = Product.objects.filter(
        is_active=True,
        created_at__gte=thirty_days_ago
    ).prefetch_related(
        Prefetch(
            'product_gallery_set',
            queryset=Product_Gallery.objects.order_by('image_order'),
            to_attr='ordered_gallery_images')
    ).select_related(
        'subcategory_id',
        'brand_id'
    ).order_by('-created_at')
    
    # Get all the necessary data for filters
    all_brands = Brand.objects.filter(is_active=True).annotate(
        product_count=Count('product')
    ).order_by('name')
    
    # Get price statistics
    price_stats = products.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    global_min_price = price_stats['min_price'] or 0
    global_max_price = price_stats['max_price'] or 1000
    
    # Prepare categories with subcategories
    categories_with_subcategories = []
    for category in Category.objects.filter(is_active=True).prefetch_related('subcategories'):
        subcategory_ids = list(category.subcategories.all().values_list('id', flat=True))
        categories_with_subcategories.append({
            'category': category,
            'subcategory_ids': subcategory_ids,
            'has_selected_subcategory': False
        })

    # Add pagination
    paginator = Paginator(products, 28)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj,
        'title': 'New Arrivals',
        'categories_with_subcategories': categories_with_subcategories,
        'sizes': Size.objects.filter(is_active=True).order_by('sort_order'),
        'brands': all_brands,
        'ordered_brands': all_brands,  # For new arrivals, we don't have selected brands
        'selected_brands': [],
        'selected_sizes': [],
        'selected_subcategory': None,
        'sort': 'date-new',  # Default sort for new arrivals
        'min_price': None,
        'max_price': None,
        'global_min_price': global_min_price,
        'global_max_price': global_max_price,
        'current_gender': None,
    }
    return render(request, 'shop.html', context)


def product_detail(request, product_id):
    try:
        product = get_object_or_404(
            Product.objects.select_related('subcategory_id', 'brand_id', 'material_id'),
            id=product_id,
            is_active=True
        )
        
        # Check if product is in user's wishlist
        in_wishlist = False
        if 'user_id' in request.session:
            in_wishlist = Wishlist.objects.filter(
                user_id=request.session['user_id'],
                product_id=product
            ).exists()
        
        # Get all active variants with size information
        variants = Product_Variants.objects.filter(
            product_id=product,
            is_active=True
        ).select_related('size_id').order_by('size_id__name')
        
        # Check stock status
        total_stock = sum(variant.stock_quantity for variant in variants)
        in_stock = total_stock > 0
        
        # Get gallery images
        gallery_images = Product_Gallery.objects.filter(
            product_id=product
        ).order_by('image_order')
        
        # Get product tags
        tags = Product_Tags.objects.filter(product_id=product)
        
        # Get related products
        related_products = Product.objects.filter(
            subcategory_id=product.subcategory_id,
            gender=product.gender,
            is_active=True
        ).exclude(id=product.id).order_by('?')[:8]
        
        # Track recently viewed
        recently_viewed_products = []
        has_purchased = False
        
        if 'user_id' in request.session:
            try:
                user = User.objects.get(id=request.session['user_id'])
            
                # Update recently viewed
                RecentlyViewed.objects.update_or_create(
                    user_id=user,
                    product_id=product,
                    defaults={'viewed_at': timezone.now()}
                )
            
                # Get recently viewed products
                recently_viewed = RecentlyViewed.objects.filter(
                    user_id=user
                ).exclude(product_id=product).select_related('product_id').order_by('-viewed_at')[:4]
            
                recently_viewed_products = [rv.product_id for rv in recently_viewed]
            
                # Check if user purchased this product
                has_purchased = Order_Details.objects.filter(
                    order_id__user_id=user,
                    product_variant_id__product_id=product
                ).exists()
            
            except User.DoesNotExist:
                messages.error(request, "Your session has expired. Please login again.")
            except Exception as e:
                print(f"Error in product detail: {str(e)}")
                
        # Get previous and next products
        prev_product = Product.objects.filter(
            id__lt=product.id, is_active=True
        ).order_by('-id').first()
    
        next_product = Product.objects.filter(
            id__gt=product.id, is_active=True
        ).order_by('id').first()
        
        # Get reviews for this product
        reviews = Review.objects.filter(product_id=product).select_related('user_id')
    
        # Calculate average rating
        average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
        # Get rating counts
        rating_counts = {}
        for rating in range(1, 6):
            rating_counts[rating] = reviews.filter(rating=rating).count()
        
        context = {
            'product': product,
            'in_wishlist': in_wishlist,
            'variants': variants,
            'in_stock': in_stock,
            'total_stock': total_stock,
            'gallery_images': gallery_images,
            'tags': tags,
            'related_products': related_products,
            'recently_viewed_products': recently_viewed_products,
            'has_purchased': has_purchased,
            'prev_product': prev_product,
            'next_product': next_product,
            'reviews': reviews,
            'average_rating': average_rating,
            'rating_counts': rating_counts,
        }
        
        return render(request, 'product_detail.html', context)
        
    except Exception as e:
        print(f"Error in product_detail: {str(e)}")
        messages.error(request, "An error occurred while loading the product.")
        return redirect('homepage')


@require_POST
def check_variant_stock(request, variant_id):
    variant = get_object_or_404(Product_Variants, id=variant_id)
    return ({
        'in_stock': variant.stock_quantity > 0,
        'stock': variant.stock_quantity,
        'price': float(variant.product_id.price + variant.additional_price),
    })


# ============================= WISHLIST VIEWS =============================


@user_login_required
def wishlist(request):
    """Display user's wishlist"""
    try:
        user_id = request.session['user_id']
        wishlist_items = Wishlist.objects.filter(
            user_id=user_id
        ).select_related(
            'product_id__brand_id'
        ).prefetch_related(
            'product_id__variants'
        ).order_by('-added_at')
        
        context = {
            'wishlist_items': wishlist_items,
            'wishlist_count': wishlist_items.count()
        }
        return render(request, 'wishlist.html', context)
        
    except Exception as e:
        messages.error(request, "Error loading your wishlist")
        return redirect('homepage')


@user_login_required
def add_to_wishlist(request, product_id):
    """Add or remove item from wishlist"""
    try:
        user_id = request.session['user_id']
        product = get_object_or_404(
            Product,
            id=product_id,
            is_active=True
        )
        
        # Check if already in wishlist
        wishlist_item = Wishlist.objects.filter(
            user_id=user_id,
            product_id=product
        ).first()
        
        if wishlist_item:
            # Item exists, so remove it
            wishlist_item.delete()
            messages.success(request, "Removed from wishlist!")
        else:
            # Add to wishlist
            Wishlist.objects.create(
                user_id_id=user_id,
                product_id=product
            )
            messages.success(request, "Added to wishlist!")
            
        return redirect('product_detail', product_id=product_id)
        
    except Exception as e:
        messages.error(request, "Error updating wishlist")
        return redirect('product_detail', product_id=product_id)


@user_login_required
def add_to_wishlist_quick_view(request, product_id):
    """Add or remove item from wishlist"""
    try:
        user_id = request.session['user_id']
        product = get_object_or_404(
            Product,
            id=product_id,
            is_active=True
        )
        
        # Check if already in wishlist
        wishlist_item = Wishlist.objects.filter(
            user_id=user_id,
            product_id=product
        ).first()
        
        if wishlist_item:
            wishlist_item.delete()
            messages.success(request, "Removed from wishlist!")
        else:
            Wishlist.objects.create(
                user_id_id=user_id,
                product_id=product
            )
            messages.success(request, "Added to wishlist!")
            
        return redirect('wishlist')
        
    except Exception as e:
        messages.error(request, "Error updating wishlist")
        return redirect('shop')


@user_login_required
def remove_from_wishlist(request, item_id):
    """Remove item from wishlist"""
    try:
        user_id = request.session['user_id']
        item = get_object_or_404(
            Wishlist,
            id=item_id,
            user_id=user_id
        )
        product_name = item.product_id.name
        item.delete()
        messages.success(request, f"Removed {product_name} from wishlist")
        return redirect('wishlist')
        
    except Exception as e:
        messages.error(request, "Error removing from wishlist")
        return redirect('wishlist')

@user_login_required
def empty_wishlist(request):
    """Remove all items from wishlist"""
    try:
        user_id = request.session['user_id']
        # Get all wishlist items for the user
        wishlist_items = Wishlist.objects.filter(user_id=user_id)
        
        if wishlist_items.exists():
            count = wishlist_items.count()
            wishlist_items.delete()
            messages.success(request, f"Removed all {count} items from your wishlist")
        else:
            messages.info(request, "Your wishlist is already empty")
            
        return redirect('wishlist')
        
    except Exception as e:
        messages.error(request, "Error emptying wishlist")
        return redirect('wishlist')
    

@user_login_required
def move_to_cart(request, item_id):
    """Move wishlist item to cart"""
    try:
        user_id = request.session['user_id']
        wishlist_item = get_object_or_404(
            Wishlist,
            id=item_id,
            user_id=user_id
        )
        
        # Get the first available variant of the product
        variant = wishlist_item.product_id.variants.first()
        
        if not variant:
            messages.warning(request, "This product is not available in any size")
            return redirect('wishlist')
        
        # Check stock
        if variant.stock_quantity < 1:
            messages.warning(request, "This item is currently out of stock")
            return redirect('wishlist')
        
        # Add to cart
        cart, created = Cart.objects.get_or_create(user_id_id=user_id)
        cart_item, item_created = Cart_Items.objects.get_or_create(
            cart_id=cart,
            product_variant_id=variant,
            defaults={
                'quantity': 1,
                'price_at_time': variant.product_id.price + (variant.additional_price or 0)
            }
        )
        
        if not item_created:
            cart_item.quantity += 1
            cart_item.save()
        
        # Remove from wishlist
        wishlist_item.delete()
        messages.success(request, "Item moved to cart successfully!")
        return redirect('cart')
        
    except Exception as e:
        print(f"Error moving to cart: {str(e)}")
        messages.error(request, "Error moving item to cart")
        return redirect('wishlist')
    
@user_login_required
def quick_add_to_wishlist(request, product_id):
    try:
        user = User.objects.get(id=request.session['user_id'])
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # Check if product is already in wishlist
        if Wishlist.objects.filter(user_id=user, product_id=product).exists():
            messages.info(request, f"{product.name} is already in your wishlist 💖")
        else:
            Wishlist.objects.create(user_id=user, product_id=product)
            messages.success(request, f"✓ {product.name} added to wishlist!")
            
    except IntegrityError:
        messages.error(request, "Couldn't add to wishlist. Please try again.")
    except Exception as e:
        messages.error(request, "An unexpected error occurred.")
        error(f"Quick add to wishlist error: {str(e)}")
           
    return redirect('shop')

@user_login_required
def quick_add_to_wishlist_home(request, product_id):
    try:
        user = User.objects.get(id=request.session['user_id'])
        product = get_object_or_404(Product, id=product_id, is_active=True)

        #Check if product is already in wishlist
        if Wishlist.objects.filter(user_id=user, product_id=product).exists():
            messages.info(request, f"{product.name} is already in your wishlist 💖")
        else:
            Wishlist.objects.create(user_id=user, product_id=product)
            messages.success(request, f"✓ {product.name} added to wishlist!")

    except IntegrityError:
        messages.error(request, "Couldn't add to wishlist. Please try again.")
    except Exception as e:
        messages.error(request, "An unexpected error occurred.")
        error(f"Quick add to wishlist error: {str(e)}")

    return redirect('homepage')

# ============================= CART VIEWS =============================


@user_login_required
@require_POST
def add_to_cart_quick_view(request, product_id):
    try:
        # Check user session
        if 'user_id' not in request.session:
            messages.error(request, 'Please login to add items to cart')
            return redirect('shop')  # Redirect to shop page without product_id

        # Get product and validate
        product = get_object_or_404(Product, id=product_id, is_active=True)
        variant_id = request.POST.get('variant_id')
        quantity = int(request.POST.get('quantity', 1))
        keep_cart_open = request.POST.get('keep_cart_open') == '1'

        if not variant_id:
            messages.error(request, 'Please select a size')
            return redirect('shop')  # Redirect to shop page

        with transaction.atomic():
            # Get and lock variant
            variant = Product_Variants.objects.select_for_update().get(
                id=variant_id,
                product_id=product_id,
                is_active=True
            )

            # Check stock
            if variant.stock_quantity < quantity:
                messages.warning(request, f'Only {variant.stock_quantity} available in stock')
                return redirect('shop')  # Redirect to shop page

            # Get or create cart
            cart, created = Cart.objects.get_or_create(user_id_id=request.session['user_id'])
            
            # Calculate price
            price = float(product.price) + float(variant.additional_price or 0)

            # Add or update cart item
            cart_item, created = Cart_Items.objects.get_or_create(
                cart_id=cart,
                product_variant_id=variant,
                defaults={
                    'quantity': quantity,
                    'price_at_time': price
                }
            )

            if not created:
                new_quantity = cart_item.quantity + quantity
                if new_quantity > variant.stock_quantity:
                    messages.warning(request, f'Cannot add more than {variant.stock_quantity} items')
                    return redirect('shop')  # Redirect to shop page
                cart_item.quantity = new_quantity
                cart_item.save()

            messages.success(request, f'Added {product.name} to your cart')
            
            # Always redirect to shop page and open cart drawer
            return redirect(f"{reverse('shop')}?open_cart_drawer=true&added_product={product_id}")

    except Product_Variants.DoesNotExist:
        messages.error(request, 'Selected size not available')
    except Exception:
        messages.error(request, 'An error occurred. Please try again.')

    return redirect('shop')  # Redirect to shop page


@user_login_required
@require_POST
def add_to_cart(request, product_id):
    try:
        # Check user session
        if 'user_id' not in request.session:
            messages.error(request, 'Please login to add items to cart')
            return redirect('product_detail', product_id=product_id)

        # Get product and validate
        product = get_object_or_404(Product, id=product_id, is_active=True)
        variant_id = request.POST.get('variant_id')
        quantity = int(request.POST.get('quantity', 1))
        keep_cart_open = request.POST.get('keep_cart_open') == '1'

        if not variant_id:
            messages.error(request, 'Please select a size')
            return redirect('product_detail', product_id=product_id)

        with transaction.atomic():
            # Get and lock variant
            variant = Product_Variants.objects.select_for_update().get(
                id=variant_id,
                product_id=product_id,
                is_active=True
            )

            # Check stock
            if variant.stock_quantity < quantity:
                messages.warning(request, f'Only {variant.stock_quantity} available in stock')
                return redirect('product_detail', product_id=product_id)

            # Get or create cart
            cart, created = Cart.objects.get_or_create(user_id_id=request.session['user_id'])
            
            # Calculate price
            price = float(product.price) + float(variant.additional_price or 0)

            # Add or update cart item
            cart_item, created = Cart_Items.objects.get_or_create(
                cart_id=cart,
                product_variant_id=variant,
                defaults={
                    'quantity': quantity,
                    'price_at_time': price
                }
            )

            if not created:
                new_quantity = cart_item.quantity + quantity
                if new_quantity > variant.stock_quantity:
                    messages.warning(request, f'Cannot add more than {variant.stock_quantity} items')
                    return redirect('product_detail', product_id=product_id)
                cart_item.quantity = new_quantity
                cart_item.save()

            messages.success(request, f'Added {product.name} to your cart')
            
            # Redirect back with parameter to open cart
            if keep_cart_open:
                return redirect(f"{reverse('product_detail', args=[product_id])}?show_cart=1")
            return redirect('product_detail', product_id=product_id)

    except Product_Variants.DoesNotExist:
        messages.error(request, 'Selected size not available')
    except Exception as e:
        messages.error(request, 'An error occurred. Please try again.')
    return redirect('product_detail', product_id=product_id)


@user_login_required
def cart(request):
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            messages.error(request, "Please login to view your cart.")
            return redirect('login')
            
        cart_obj, created = Cart.objects.get_or_create(user_id_id=user_id)
        cart_items = Cart_Items.objects.filter(cart_id=cart_obj).select_related(
            'product_variant_id__product_id', 
            'product_variant_id__size_id'
        ).order_by('-id')

        cart_total = Decimal('0')
        total_gst = Decimal('0')
        total_base_price = Decimal('0')
        shipping_charge = Decimal('69')  # Fixed shipping charge

        for item in cart_items:
            gst_inclusive_price = item.price_at_time
            quantity = Decimal(item.quantity)
            
            # Calculate base price and GST based on product price
            if gst_inclusive_price >= Decimal('1000'):
                # For items >= ₹1000 (12% GST)
                base_price = gst_inclusive_price / Decimal('1.12')
                gst_amount = gst_inclusive_price - base_price
            else:
                # For items < ₹1000 (5% GST)
                base_price = gst_inclusive_price / Decimal('1.05')
                gst_amount = gst_inclusive_price - base_price
            
            # Calculate totals for this item
            item_base_total = base_price * quantity
            item_gst_total = gst_amount * quantity
            item_total = gst_inclusive_price * quantity
            
            # Add to cart totals
            total_base_price += item_base_total
            total_gst += item_gst_total
            cart_total += item_total
        
        # Round values to 2 decimal places
        total_base_price = total_base_price.quantize(Decimal('0.00'))
        total_gst = total_gst.quantize(Decimal('0.00'))
        cart_total = cart_total.quantize(Decimal('0.00'))
        grand_total = cart_total + shipping_charge

        context = {
            'cart_items': cart_items,
            'base_price_total': total_base_price,
            'cart_total': cart_total,
            'total_gst': total_gst,
            'shipping_charge': shipping_charge,
            'grand_total': grand_total,
            'cart_count': cart_items.count()
        }
        return render(request, 'cart.html', context)
        
    except Exception as e:
        messages.error(request, "An error occurred while loading your cart.")
        error(f"Cart error: {str(e)}")
        return redirect('homepage')    


@user_login_required
def update_cart_item_drawer(request):
    if request.method == 'POST' and request.user.is_authenticated:
        referer = request.META.get('HTTP_REFERER', 'home')
        try:
            cart_item_id = request.POST.get('cart_item_id')
            quantity = int(request.POST.get('quantity'))
            keep_drawer_open = request.POST.get('keep_drawer_open') == 'true'
            
            if quantity < 1:
                messages.error(request, 'Quantity must be at least 1')
                if keep_drawer_open:
                    return redirect(referer + '?open_cart_drawer=true')
                return redirect(referer)
            
            cart_item = Cart_Items.objects.get(
                id=cart_item_id,
                cart_id__user_id=request.user.id
            )
            
            # Update only the quantity
            cart_item.quantity = quantity
            cart_item.save()  # total_price should update automatically if it's a property
            
            messages.success(request, 'Cart updated successfully')
            
        except Cart_Items.DoesNotExist:
            messages.error(request, 'Item not found in your cart')
        except ValueError:
            messages.error(request, 'Invalid quantity')
        except Exception as e:
            messages.error(request, 'An error occurred while updating the cart')
    
    # Check if we need to keep drawer open
    keep_drawer_open = request.POST.get('keep_drawer_open') == 'true'
    if keep_drawer_open:
        return redirect(referer + '?open_cart_drawer=true')
    
    return redirect(referer)


@user_login_required
def remove_cart_item_drawer(request, product_id, variant_id):
    user_id = request.session.get('user_id')
    if user_id:
        try:
            cart = Cart.objects.get(user_id=user_id)
            item = Cart_Items.objects.get(
                cart_id=cart,
                product_variant_id__product_id=product_id,
                product_variant_id=variant_id
            )
            product_name = item.product_variant_id.product_id.name
            item.delete()
            messages.success(request, f"'{product_name[:20]}...' removed from cart")
        except (Cart.DoesNotExist, Cart_Items.DoesNotExist):
            messages.error(request, "Item not found in your cart")
    
    referer = request.META.get('HTTP_REFERER', 'home')
    
    # Check if we need to keep drawer open
    if request.GET.get('open_cart_drawer') == 'true':
        return redirect(referer + '?open_cart_drawer=true')
        
    return redirect(referer)


@user_login_required
@require_POST
def update_cart_item(request):
    try:
        user_id = request.session['user_id']
        item_id = request.POST.get('cart_item_id')
        quantity = int(request.POST.get('quantity', 1))
        
        cart = Cart.objects.get(user_id_id=user_id)
        cart_item = Cart_Items.objects.get(id=item_id, cart_id=cart)
        
        # Validate stock
        if quantity > cart_item.product_variant_id.stock_quantity:
            messages.warning(request, f"Only {cart_item.product_variant_id.stock_quantity} available in stock")
            return redirect('cart')
        
        # Update or remove
        if quantity <= 0:
            cart_item.delete()
            messages.success(request, "Item removed from cart")
        else:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, "Cart updated successfully")
            
        return redirect('cart')
        
    except Exception as e:
        messages.error(request, "Error updating cart item")
        return redirect('cart')
    

@user_login_required
def remove_cart_item(request, product_id, variant_id):
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            messages.error(request, "Please login to modify your cart.")
            return redirect('login')
            
        cart_obj = Cart.objects.get(user_id_id=user_id)
        cart_item = Cart_Items.objects.get(
            cart_id=cart_obj,
            product_variant_id__product_id=product_id,
            product_variant_id__id=variant_id
        )
        
        product_name = cart_item.product_variant_id.product_id.name
        cart_item.delete()
        
        messages.success(request, f"{product_name} removed from your cart.")
        return redirect('cart')
        
    except Cart.DoesNotExist:
        messages.error(request, "Your cart was not found.")
    except Cart_Items.DoesNotExist:
        messages.error(request, "Item not found in cart.")
    except Exception as e:
        messages.error(request, "An error occurred while removing item from cart.")
    
    return redirect('cart')


@user_login_required
def empty_cart(request):
    try:
        user_id = request.session.get('user_id')
        cart = Cart.objects.get(user_id_id=user_id)
        count = Cart_Items.objects.filter(cart_id=cart).count()
        
        if count == 0:
            messages.info(request, "Your cart is already empty")
            return redirect('cart')
            
        Cart_Items.objects.filter(cart_id=cart).delete()
        cart.updated_at = timezone.now()
        cart.save()
        
        messages.success(request, f"Removed all {count} items from your cart")
        return redirect('cart')
        
    except Cart.DoesNotExist:
        messages.error(request, "No cart found to empty")
    except Exception as e:
        messages.error(request, "Failed to empty cart")
        error(f"Empty cart error: {str(e)}")
    
    return redirect('cart')


@user_login_required
def move_to_wishlist(request, item_id):
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            messages.error(request, "User not logged in")
            return redirect('cart')
            
        print(f"Looking for cart item ID: {item_id} for user ID: {user_id}")
        
        # Get the cart item
        cart_item = Cart_Items.objects.get(id=item_id, cart_id__user_id=user_id)
        print(f"Found cart item: {cart_item}")
        
        # Get the product from the cart item
        product = cart_item.product_variant_id.product_id
        print(f"Product to add to wishlist: {product}")
        
        # Check if this product is already in the user's wishlist
        existing_wishlist_item = Wishlist.objects.filter(
            user_id=user_id,
            product_id=product
        ).first()
        
        if existing_wishlist_item:
            messages.info(request, "This product is already in your wishlist")
        else:
            # Add to wishlist
            Wishlist.objects.create(
                user_id_id=user_id,
                product_id=product,
                added_at=timezone.now()
            )
            messages.success(request, "Item moved to wishlist successfully")
        
        # Remove from cart
        cart_item.delete()
        print("Cart item deleted successfully")
        
    except Cart_Items.DoesNotExist:
        print(f"Cart item with ID {item_id} not found for user {user_id}")
        messages.error(request, "Cart item not found")
    except Exception as e:
        print(f"Error moving item to wishlist: {str(e)}")
        messages.error(request, f"Error moving item to wishlist: {str(e)}")
    
    return redirect('wishlist')

@user_login_required
def quick_add_to_cart(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        variant = product.variants.filter(is_active=True).first()
        
        if not variant:
            messages.error(request, "This product is currently unavailable.")
            return redirect('shop')
        
        if variant.stock_quantity <= 0:
            messages.warning(request, f"Sorry, {product.name} is out of stock.")
            return redirect('shop')
        
        user = User.objects.get(id=request.session['user_id'])
        # Get or create user's cart
        cart, created = Cart.objects.get_or_create(user_id=user)
        
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
        error(f"Quick add from grid error: {str(e)}")
           
    # Redirect back to shop with parameter to open cart drawer
    shop_url = reverse('shop')
    return redirect(f"{shop_url}?open_cart_drawer=true")

@user_login_required
def quick_add_to_cart_home(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        variant = product.variants.filter(is_active=True).first()
        
        if not variant:
            messages.error(request, "This product is currently unavailable.")
            return redirect('homepage')
        
        if variant.stock_quantity <= 0:
            messages.warning(request, f"Sorry, {product.name} is out of stock.")
            return redirect('homepage')
        
        user = User.objects.get(id=request.session['user_id'])
        # Get or create user's cart
        cart, created = Cart.objects.get_or_create(user_id=user)
        
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
        error(f"Quick add from grid error: {str(e)}")
           
    # Redirect back to shop with parameter to open cart drawer
    homepage_url = reverse('homepage')
    return redirect(f"{homepage_url}?open_cart_drawer=true")

# ============================= CHECKOUT & ORDER PROCESSING =============================


def get_cart_totals(cart_items):
    """Helper function to calculate cart totals"""
    cart_total = Decimal('0')
    total_gst = Decimal('0')
    total_base_price = Decimal('0')
    shipping_charge = Decimal('69')  # Fixed shipping charge

    for item in cart_items:
        gst_inclusive_price = item.price_at_time
        quantity = Decimal(item.quantity)
        
        # Calculate base price and GST based on product price
        if gst_inclusive_price >= Decimal('1000'):
            # For items >= ₹1000 (12% GST)
            base_price = gst_inclusive_price / Decimal('1.12')
            gst_amount = gst_inclusive_price - base_price
        else:
            # For items < ₹1000 (5% GST)
            base_price = gst_inclusive_price / Decimal('1.05')
            gst_amount = gst_inclusive_price - base_price
        
        # Calculate totals for this item
        item_base_total = base_price * quantity
        item_gst_total = gst_amount * quantity
        item_total = gst_inclusive_price * quantity
        
        # Add to cart totals
        total_base_price += item_base_total
        total_gst += item_gst_total
        cart_total += item_total
    
    # Round values to 2 decimal places
    total_base_price = total_base_price.quantize(Decimal('0.00'))
    total_gst = total_gst.quantize(Decimal('0.00'))
    cart_total = cart_total.quantize(Decimal('0.00'))
    grand_total = cart_total + shipping_charge
    
    return {
        'base_price_total': total_base_price,
        'cart_total': cart_total,
        'total_gst': total_gst,
        'shipping_charge': shipping_charge,
        'grand_total': grand_total,
    }


@user_login_required
def checkout(request):
    try:
        user_id = request.session.get('user_id')
        user = User.objects.get(id=user_id)
        
        # Get user's cart
        cart_obj, created = Cart.objects.get_or_create(user_id_id=user_id)
        cart_items = Cart_Items.objects.filter(cart_id=cart_obj).select_related(
            'product_variant_id__product_id', 
            'product_variant_id__size_id'
        )
        
        if not cart_items.exists():
            messages.error(request, "Your cart is empty. Add items to proceed to checkout.")
            return redirect('cart')
        
        # Calculate cart totals
        cart_data = get_cart_totals(cart_items)
        
        # Get user addresses
        user_addresses = User_Address.objects.filter(user_id=user)
        default_address = user_addresses.filter(is_default=True).first()
        
        if request.method == 'POST':
            # Process the checkout form
            address_id = request.POST.get('address_id')
            payment_method = request.POST.get('payment_method', 'cod')
            
            # Get or create address
            selected_address = None
            if address_id and address_id != 'new':
                # Use existing address
                try:
                    selected_address = User_Address.objects.get(id=address_id, user_id=user)
                except User_Address.DoesNotExist:
                    messages.error(request, "Selected address not found.")
                    return redirect('checkout')
            
            # Create order using transaction to ensure data consistency
            try:
                with transaction.atomic():
                    
                    # ==================== NEW LOGIC START ====================
                    # Before creating a new order, find and cancel any recent 'processing' orders
                    # from this user to release stock and prevent duplicates.
                    # We'll set a tight threshold, like 15 minutes.
                    
                    threshold = timezone.now() - timedelta(minutes=15)
                    recent_processing_orders = Order_Master.objects.filter(
                        user_id=user,
                        status='processing',
                        created_at__gte=threshold
                    )

                    if recent_processing_orders.exists():
                        info(f"User {user.username} has {recent_processing_orders.count()} recent incomplete orders. Cancelling them before creating a new one.")
                        for old_order in recent_processing_orders:
                            # We use the cancel_and_restock method we created earlier.
                            # This marks the order as 'cancelled' AND restocks the items.
                            old_order.cancel_and_restock()
                    # ===================== NEW LOGIC END =====================
                    
                    # --- First, check stock for all items BEFORE creating the order ---
                    for cart_item in cart_items:
                        variant = cart_item.product_variant_id
                        if variant.stock_quantity < cart_item.quantity:
                            messages.error(request, f"Sorry, we don't have enough stock for {variant.product_id.name}. Only {variant.stock_quantity} left.")
                            return redirect('cart')
                        
                    # Create order master
                    order = Order_Master(
                        user_id=user,
                        subtotal=cart_data['cart_total'],
                        tax_amount=cart_data['total_gst'],
                        shipping_charge=cart_data['shipping_charge'],
                        total_amount=cart_data['grand_total'],
                        status='processing',  # Set to processing for online payments
                        mode_of_payment=payment_method
                    )
                    order.save()
                    
                    # Create order address
                    order_address = Order_Address(
                        order_id=order,
                        address_type=selected_address.address_type,
                        full_name=selected_address.full_name,
                        phone=selected_address.phone,
                        address_line_1=selected_address.address_line_1,
                        address_line_2=selected_address.address_line_2,
                        city=selected_address.city,
                        state=selected_address.state,
                        pincode=selected_address.pincode
                    )
                    order_address.save()
                    
                    # Create order details
                    order_details_list = []
                    for cart_item in cart_items:
                        order_detail = Order_Details.objects.create(
                            order_id=order,
                            product_variant_id=cart_item.product_variant_id,
                            quantity=cart_item.quantity,
                            unit_price=cart_item.price_at_time,
                            total_price=cart_item.total_price,
                            product_name=cart_item.product_variant_id.product_id.name,
                            product_sku=cart_item.product_variant_id.sku,
                        )
                        order_details_list.append(order_detail)
                        
                        # --- [CORRECTED] Decrement the stock for the purchased variant ---
                        variant = cart_item.product_variant_id
                        variant.stock_quantity -= cart_item.quantity
                        variant.save()
                    
                    # Handle different payment methods
                    if payment_method == 'cod':
                        # Create payment record for COD
                        Payment.objects.create(
                            payment_id=f"PAY-{int(time.time())}-{order.id}",
                            order_id=order,
                            user_id=user,
                            amount=cart_data['grand_total'],
                            payment_method='COD',
                            payment_gateway='N/A',
                            status='pending'
                        )
                        order.status = 'confirmed'  # For COD, we can confirm immediately
                        order.save()
                        
                        # Clear the cart
                        cart_items.delete()
                        
                        # Send confirmation email
                        try:
                            send_order_confirmation_email(order, order_details_list, order_address)
                            info(f"Order confirmation email sent for order {order.order_number} to {user.email}")
                        except Exception as email_error:
                            error(f"Failed to send order confirmation email: {str(email_error)}")
                        
                        messages.success(request, 'Your order has been placed successfully!')
                        return redirect('orderconfirm', order_id=order.id)
                    
                    elif payment_method in ['online', 'upi']:
                        # Create a pending payment record for online payments
                        payment = Payment.objects.create(
                            payment_id=f"PAY-{int(time.time())}-{order.id}",
                            order_id=order,
                            user_id=user,
                            amount=cart_data['grand_total'],
                            payment_method='ONLINE' if payment_method == 'online' else 'UPI',
                            payment_gateway='Razorpay',
                            status='pending'
                        )
                        
                        # Create Razorpay order
                        razorpay_order = client.order.create({
                            'amount': int(cart_data['grand_total'] * 100),  # Amount in paise
                            'currency': 'INR',
                            'receipt': order.order_number,
                            'notes': {
                                'order_id': order.id,
                                'payment_id': payment.payment_id,
                                'user_id': user.id
                            }
                        })
                        
                        # Update payment with gateway order ID
                        payment.gateway_order_id = razorpay_order['id']
                        payment.save()
                        
                        # Store order details in session for payment verification
                        request.session['razorpay_order_id'] = razorpay_order['id']
                        request.session['order_id'] = order.id
                        
                        # Render payment page with Razorpay details
                        context = {
                            'order': order,
                            'razorpay_order_id': razorpay_order['id'],
                            'razorpay_amount': int(cart_data['grand_total'] * 100),
                            'razorpay_currency': 'INR',
                            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                            'callback_url': request.build_absolute_uri(reverse('payment_handler')),
                        }
                        return render(request, 'payment.html', context)
                    
            except Exception as e:
                messages.error(request, "An error occurred while processing your order. Please try again.")
                error(f"Order creation failed for user {user.username}: {str(e)}")
                return redirect('checkout')
        
        context = {
            'cart_items': cart_items,
            'base_price_total': cart_data['base_price_total'],
            'cart_total': cart_data['cart_total'],
            'total_gst': cart_data['total_gst'],
            'shipping_charge': cart_data['shipping_charge'],
            'grand_total': cart_data['grand_total'],
            'user_addresses': user_addresses,
            'default_address': default_address,
        }
        
        return render(request, 'checkout.html', context)
        
    except Exception as e:
        messages.error(request, "An error occurred while loading checkout.")
        error(f"Checkout error for user {request.session.get('user_id')}: {str(e)}")
        return redirect('cart')


# ============================= PAYMENT HANDLER & ORDER CONFIRMATION =============================


def payment_handler(request):
    if request.method == "POST":
        try:
            # Get the payment details from the request
            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')
            
            # Verify payment signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            # Verify the payment signature
            try:
                client.utility.verify_payment_signature(params_dict)
                
                # Signature verification successful
                payment = Payment.objects.get(gateway_order_id=razorpay_order_id)
                order = payment.order_id
                
                # Update payment details
                payment.gateway_payment_id = payment_id
                payment.gateway_signature = signature
                payment.status = 'completed'
                payment.save()
                
                # Update order status
                order.status = 'confirmed'
                order.save()
                
                # Clear the cart
                user_id = request.session.get('user_id')
                try:
                    cart_obj = Cart.objects.get(user_id_id=user_id)
                    Cart_Items.objects.filter(cart_id=cart_obj).delete()
                except Cart.DoesNotExist:
                    pass
                
                # Send confirmation email
                order_details = Order_Details.objects.filter(order_id=order)
                order_address = Order_Address.objects.filter(order_id=order).first()
                
                try:
                    send_order_confirmation_email(order, order_details, order_address)
                except Exception as email_error:
                    error(f"Failed to send order confirmation email: {str(email_error)}")
                
                # Redirect to success page
                return redirect(reverse('orderconfirm', kwargs={'order_id': order.id}) + '?payment_status=success')
                
            except razorpay.errors.SignatureVerificationError:
                # Signature verification failed
                payment = Payment.objects.get(gateway_order_id=razorpay_order_id)
                payment.status = 'failed'
                payment.failure_reason = 'Signature verification failed'
                payment.save()
                
                messages.error(request, 'Payment verification failed. Please try again.')
                return redirect(reverse('checkout') + '?payment_status=failed')
                
        except Payment.DoesNotExist:
            messages.error(request, 'Invalid payment request.')
            return redirect(reverse('checkout') + '?payment_status=failed')
        except Exception as e:
            error(f"Payment processing error: {str(e)}")
            messages.error(request, 'An error occurred during payment processing.')
            return redirect(reverse('checkout') + '?payment_status=failed')
    
    return redirect('checkout')


def send_order_confirmation_email(order, order_details, order_address):
    """
    Send professional order confirmation email with invoice
    """
    try:
        # Email subject
        subject = f'Order Confirmation - {order.order_number} | VibeDrobe'
        
        # From email (use your configured email)
        from_email = settings.DEFAULT_FROM_EMAIL
        
        # To email (customer's email)
        to_email = [order.user_id.email]
        
        # Context for email template
        context = {
            'order': order,
            'order_details': order_details,
            'order_address': order_address,
            'company_name': 'VibeDrobe',
            'support_email': 'support@vibedrobe.com',
            'website_url': 'https://www.vibedrobe.com',
        }
        
        # Render HTML email template
        html_content = render_to_string('emails/order_confirmation.html', context)
        
        # Create plain text version (fallback)
        plain_text_content = f"""
Thank you for your order!

Hi {order_address.full_name},

Your order has been confirmed and is being processed.

Order Details:
- Order Number: {order.order_number}
- Date: {order.order_date.strftime('%d/%m/%Y')}
- Total Amount: ₹{order.total_amount:.2f}
- Payment Method: {order.get_mode_of_payment_display() if hasattr(order, 'get_mode_of_payment_display') else order.mode_of_payment.title()}

Shipping Address:
{order_address.full_name}
{order_address.address_line_1}
{order_address.address_line_2 if order_address.address_line_2 else ''}
{order_address.city}, {order_address.state} - {order_address.pincode}
Phone: {order_address.phone}

Items Ordered:"""
        
        for item in order_details:
            plain_text_content += f"\n- {item.product_name} × {item.quantity} - ₹{item.total_price:.2f}"
        
        plain_text_content += f"""

Subtotal: ₹{order.subtotal:.2f}
GST: ₹{order.tax_amount:.2f}
Shipping: ₹{order.shipping_charge:.2f}
Total: ₹{order.total_amount:.2f}

Thank you for choosing VibeDrobe!

For support, contact us at support@vibedrobe.com
"""
        
        # Create email message
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_text_content,
            from_email=from_email,
            to=to_email,
        )
        
        # Attach HTML content
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send(fail_silently=False)
        
        return True
        
    except Exception as e:
        return False


@user_login_required
def orderconfirm(request, order_id):
    try:
        user_id = request.session.get('user_id')
        user = User.objects.get(id=user_id)
        
        # Get the order with related data
        order = get_object_or_404(Order_Master, id=order_id, user_id=user)
        order_details = Order_Details.objects.filter(order_id=order)
        order_address = Order_Address.objects.filter(order_id=order).first()
        payment = Payment.objects.filter(order_id=order).first()
        
        context = {
            'order': order,
            'order_details': order_details,
            'order_address': order_address,
            'payment': payment,
        }
        
        return render(request, 'orderconfirm.html', context)
        
    except Exception as e:
        messages.error(request, "Order not found or you don't have permission to view this order.")
        return redirect('homepage')


@user_login_required
def add_review(request, order_id, product_id):
    # --- 1. Fetch the logged-in user from the session ---
    try:
        user = User.objects.get(id=request.session.get('user_id'))
    except User.DoesNotExist:
        messages.error(request, "User not found. Please log in again.")
        return redirect('login_register')

    # --- 2. Get the necessary order and product objects ---
    order = get_object_or_404(Order_Master, id=order_id)
    product = get_object_or_404(Product, id=product_id)

    # --- 3. SECURITY & LOGIC CHECKS ---
    # THE FIX IS HERE: Use order.user_id to match your model's field name
    if order.user_id != user:
        messages.error(request, "You are not authorized to review this order.")
        return redirect('account_orders')

    if order.status != 'delivered':
        messages.error(request, "You can only review products from delivered orders.")
        return redirect('account_orders')

    if not Order_Details.objects.filter(order_id=order, product_variant_id__product_id=product).exists():
        messages.error(request, "This product is not part of the specified order.")
        return redirect('account_orders')
        
    if Review.objects.filter(order_id=order, product_id=product, user_id=user).exists():
        messages.warning(request, "You have already submitted a review for this product.")
        return redirect('account_orders')

    # --- 4. FORM HANDLING ---
    if request.method == 'POST':
        rating = request.POST.get('rating')
        title = request.POST.get('title')
        comment = request.POST.get('comment')

        if not rating:
            messages.error(request, "Please select a star rating.")
        else:
            # Use your model's field names when creating the review
            Review.objects.create(
                product_id=product,
                user_id=user,
                order_id=order,
                rating=rating,
                title=title,
                comment=comment
            )
            messages.success(request, f"Your review for '{product.name}' has been submitted. Thank you!")
            return redirect('account_orders')

    context = {
        'product': product,
        'order': order
    }
    return render(request, 'add_review.html', context)
# ============================= STATIC PAGES =============================

def contactus(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        # Basic validation
        if not name or not email or not message:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'contactus.html')
        
        # Send email
        try:
            # Email to admin
            subject = f"Contact Form Submission from {name}"
            message_body = f"""
            Name: {name}
            Email: {email}
            Message: {message}
            """
            
            send_mail(
                subject,
                message_body,
                settings.DEFAULT_FROM_EMAIL,
                [settings.CONTACT_EMAIL],  # Make sure to add this to your settings
                fail_silently=False,
            )
            
            # Optional: Send confirmation email to user
            user_subject = "Thank you for contacting VibeDrobe"
            user_message = f"""
            Dear {name},
            
            Thank you for reaching out to us. We have received your message and will get back to you within 24-48 hours.
            
            Your message:
            {message}
            
            Best regards,
            VibeDrobe Team
            """
            
            send_mail(
                user_subject,
                user_message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            messages.success(request, 'Your message has been sent successfully! We will get back to you soon.')
            return redirect('contactus')
            
        except BadHeaderError:
            messages.error(request, 'Invalid header found.')
            return render(request, 'contactus.html')
        except Exception as e:
            messages.error(request, f'There was an error sending your message: {str(e)}')
            return render(request, 'contactus.html')
    
    return render(request, 'contactus.html')

def aboutus(request):
   return render(request, 'aboutus.html')