# razorpay_utils.py
import razorpay
from django.conf import settings
from .utils import info, error, success

def get_razorpay_client():
    """Initialize and return Razorpay client"""
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        return client
    except Exception as e:
        error(f"Error initializing Razorpay client: {str(e)}")
        return None

def create_razorpay_order(amount, currency='INR', receipt=None):
    """Create a Razorpay order"""
    try:
        client = get_razorpay_client()
        if not client:
            return None
            
        data = {
            'amount': int(amount * 100),  # Convert to paise
            'currency': currency,
            'payment_capture': 1  # Auto capture payment
        }
        
        if receipt:
            data['receipt'] = receipt
            
        order = client.order.create(data=data)
        info(f"Razorpay order created: {order.get('id')}")
        return order
        
    except Exception as e:
        error(f"Error creating Razorpay order: {str(e)}")
        return None

def verify_razorpay_payment(payment_id, order_id, signature):
    """Verify Razorpay payment signature"""
    try:
        client = get_razorpay_client()
        if not client:
            return False
            
        params = {
            'razorpay_payment_id': payment_id,
            'razorpay_order_id': order_id,
            'razorpay_signature': signature
        }
        
        return client.utility.verify_payment_signature(params)
        
    except Exception as e:
        error(f"Error verifying payment signature: {str(e)}")
        return False