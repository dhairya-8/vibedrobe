# userside/context_processors.py
from django.contrib.messages import constants as messages

def custom_message_tags(request):
    return {
        'MESSAGE_TAGS': {
            messages.DEBUG: 'info',
            messages.INFO: 'info',
            messages.SUCCESS: 'success',
            messages.WARNING: 'warning',
            messages.ERROR: 'error',
        }
    }
