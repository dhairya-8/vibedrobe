from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

def user_login_required(view_func):
    """
    Enhanced decorator that works with both session and auth
    """
    def wrapper(request, *args, **kwargs):
        # Check session (your existing way)
        if 'user_id' not in request.session:
            messages.error(request, 'Please login to access this page')
            return redirect('login_register')
        
        # Additional auth check (optional but recommended)
        if not request.user.is_authenticated:
            messages.error(request, 'Session expired, please login again')
            return redirect('login_register')
            
        return view_func(request, *args, **kwargs)
    return wrapper