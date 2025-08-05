# userside/context_processors.py
from django.contrib.messages import constants as messages
from adminside.models import *

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
    
def cart_context(request):
    context = {}
    
    if 'user_id' in request.session:
        try:
            cart = Cart.objects.filter(user_id_id=request.session['user_id']).first()
            if cart:
                cart_items = Cart_Items.objects.filter(cart_id=cart).select_related(
                    'product_variant_id__product_id',
                    'product_variant_id__size_id'
                )
                context.update({
                    'cart_count': cart_items.count(),
                    'cart_items': cart_items,
                    'cart_total': sum(item.price_at_time * item.quantity for item in cart_items),
                })
        except Exception as e:
            print(f"Error in cart context: {str(e)}")
        
    return context
