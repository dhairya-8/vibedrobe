from .models import Admin

def admin_profile_image(request):
    admin = None
    profile_image_url = None
    if request.session.get('admin_id'):
        try:
            admin = Admin.objects.get(id=request.session.get('admin_id'))
            if admin.profile_image:
                profile_image_url = admin.profile_image.url
        except Admin.DoesNotExist:
            pass
    return {
        'admin_profile_image_url': profile_image_url
    }
