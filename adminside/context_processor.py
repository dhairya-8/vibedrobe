from .models import Admin
from django.contrib.messages import get_messages
from django.contrib.messages import constants as messages

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

#  Custom alert

def custom_alerts(request):
    """
    Context processor to make custom alert data available in all templates
    """
    
    def get_alert_class(message_level):
        # Add shadow and border as per theme
        class_mapping = {
            messages.SUCCESS: 'alert alert-success shadow-sm border-theme-white-2',
            messages.ERROR: 'alert alert-danger shadow-sm border-theme-white-2',
            messages.WARNING: 'alert alert-warning shadow-sm border-theme-white-2',
            messages.INFO: 'alert alert-purple shadow-sm border-theme-white-2',
            messages.DEBUG: 'alert alert-purple shadow-sm border-theme-white-2',
        }
        return class_mapping.get(message_level, 'alert alert-purple shadow-sm border-theme-white-2')


    
    def get_icon_circle_html(message_level):
        # Icon circle background and icon, as per theme
        icon_mapping = {
        messages.SUCCESS: (
            'bg-success', 'fas fa-check', 'Well done!'
        ),
        messages.ERROR: (
            'bg-danger', 'fas fa-xmark', 'Oh snap!'
        ),
        messages.WARNING: (
            'bg-warning', 'fas fa-exclamation', 'Warning!'
        ),
        messages.INFO: (
            'bg-purple', 'fas fa-info', 'Info'
        ),
        messages.DEBUG: (
            'bg-purple', 'fas fa-info', 'Debug'
        ),
        }
        bg_class, icon_class, strong_text = icon_mapping.get(
        message_level, ('bg-purple', 'fas fa-info', 'Notice')
        )
        return {
        'circle_html': f'''<div class="d-inline-flex justify-content-center align-items-center thumb-xs {bg_class} rounded-circle mx-auto me-1">
            <i class="{icon_class} align-self-center mb-0 text-white"></i>
        </div>''',
        'strong_text': strong_text
    }
    
    # Get messages from request
    message_list = get_messages(request)
    
    processed_messages = []
    for message in message_list:
        icon_data = get_icon_circle_html(message.level)
        processed_messages.append({
            'message': message.message,
            'level': message.level,
            'level_tag': message.level_tag,
            'alert_class': get_alert_class(message.level),
            'icon_circle_html': icon_data['circle_html'],
            'strong_text': icon_data['strong_text'],
            'tags': message.tags,
        })
    
    return {
        'custom_messages': processed_messages,
    }