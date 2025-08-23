from django.contrib import messages
from django.contrib.messages import constants
from adminside.models import Cart, Cart_Items, Wishlist
from django.shortcuts import redirect

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
    context = {}
    cart_count = 0
    wishlist_count = 0
    
    if 'user_id' in request.session:
        user_id = request.session['user_id']
        
        try:
            cart = Cart.objects.get(user_id=user_id)
            cart_count = Cart_Items.objects.filter(cart_id=cart).count()
        except Cart.DoesNotExist:
            pass
        
        wishlist_count = Wishlist.objects.filter(user_id=user_id).count()
    
    context['cart_count'] = cart_count
    context['wishlist_count'] = wishlist_count
    
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
            cart_items = Cart_Items.objects.filter(cart_id=cart).select_related(
                'product_variant_id__product_id',
                'product_variant_id__size_id'
            )
            
            cart_data['cart_items_count'] = cart_items.count()
            subtotal = 0
            
            for item in cart_items:
                subtotal += item.total_price
                cart_data['cart_items'].append({
                    'id': item.id,
                    'image': item.product_variant_id.product_id.base_image.url,
                    'name': item.product_variant_id.product_id.name,
                    'color': item.product_variant_id.product_id.color,
                    'size': item.product_variant_id.size_id.name,
                    'quantity': item.quantity,
                    'price': item.price_at_time,
                    'total_price': item.total_price,
                    'remove_url': f"/remove-cart-item-drawer/{item.product_variant_id.product_id.id}/{item.product_variant_id.id}/"
                })
            
            cart_data['cart_subtotal'] = subtotal
            
        except Cart.DoesNotExist:
            pass
    
    return {'cart_drawer_data': cart_data}