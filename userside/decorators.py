from django.shortcuts import redirect
from django.contrib import messages

def user_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            messages.error(request, 'Please login to access this page')
            return redirect('login_register')
        return view_func(request, *args, **kwargs)
    return wrapper
