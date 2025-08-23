from django.contrib import messages
from django.contrib.messages import constants
from django.urls import reverse
from adminside.models import Cart, Cart_Items, Wishlist

def custom_message_tags(request):
    return {
        'MESSAGE_TAGS': {
            constants.DEBUG: 'info',
            constants.INFO: 'info',
            constants.SUCCESS: 'success',
            constants.WARNING: 'warning',
            constants.ERROR: 'error',
        }
    }

def cart_and_wishlist_count(request):
    context = {'cart_count': 0, 'wishlist_count': 0}
    if 'user_id' in request.session:
        user_id = request.session['user_id']
        context['cart_count'] = Cart_Items.objects.filter(
            cart_id__user_id=user_id).count()
        context['wishlist_count'] = Wishlist.objects.filter(
            user_id=user_id).count()
    return context

def cart_drawer(request):
    cart_data = {
        'cart_items_count': 0,
        'cart_items': [],
        'cart_subtotal': 0
    }
    
    if 'user_id' in request.session:
        try:
            cart = Cart.objects.get(user_id=request.session['user_id'])
            items = Cart_Items.objects.filter(cart_id=cart).select_related(
                'product_variant_id__product_id',
                'product_variant_id__size_id'
            )
            
            cart_data['cart_items_count'] = items.count()
            cart_data['cart_items'] = [{
                'id': item.id,
                'image': item.product_variant_id.product_id.base_image.url,
                'name': item.product_variant_id.product_id.name,
                'color': item.product_variant_id.product_id.color,
                'size': item.product_variant_id.size_id.name,
                'quantity': item.quantity,
                'price': item.price_at_time,
                'total_price': item.total_price,
                'remove_url': reverse('remove_cart_item', args=[
                    item.product_variant_id.product_id.id,
                    item.product_variant_id.id
                ])
            } for item in items]
            
            cart_data['cart_subtotal'] = sum(item.total_price for item in items)
            
        except Cart.DoesNotExist:
            pass
            
    return {'cart_drawer_data': cart_data}