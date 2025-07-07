import re
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.utils import timezone
from adminside.models import *

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
   return render(request, 'shop.html')

def product_detail(request):
   return render(request, 'product_detail.html')

def cart(request):
   return render(request,'cart.html')

def user_login(request):
   return render(request, 'user_login.html')

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