from django.shortcuts import redirect
from django.contrib import messages

def admin_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if 'admin_id' not in request.session:
            messages.error(request, 'Please login to access this page')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper