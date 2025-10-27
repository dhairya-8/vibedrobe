# adminside/management/commands/seed_dummy_orders.py

import random
import string
import uuid
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

from adminside.models import (
    User, User_Address, Product, Product_Variants, 
    Order_Master, Order_Details, Order_Address, 
    Shipping, Payment
)

class Command(BaseCommand):
    help = 'Seeds the database with realistic dummy users, addresses, orders, shipping, and payments.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("🚀 Starting ENHANCED data seeding process..."))

        fake = Faker('en_IN')

        # --- PRODUCT CLUSTERS ---
        PRODUCT_CLUSTERS = [
            [791, 766, 763],
            [790, 788, 786],
            [789, 787, 783],
            [785, 784, 778],
            [781, 775, 774],
            [1, 60, 138, 140, 236],
            [2, 62, 63, 67, 71],
            [3, 84, 512, 517, 518],
            [4, 67, 71, 72, 73, 75],
            [5, 68, 69, 70, 74],
            [6, 7, 101, 104],
            [7, 102, 313, 314, 315],
            [8, 77, 78, 79, 81, 106],
            [9, 236, 237, 238, 239],
            [10, 320, 324, 331, 332],
            [11, 242, 243, 510, 640],
            [12, 6, 104, 7, 14],
            [13, 143, 244, 15, 14, 7],
            [14, 586, 587, 629, 630],
            [15, 7, 14, 143, 244],
            [16, 635, 636, 637, 638],
            [17, 13, 15, 87, 99],
            [18, 23, 106, 130, 137],
            [19, 1, 9, 70, 74, 76],
            [20, 6, 7, 101, 104],
            [21, 18, 23, 106, 130, 137],
            [22, 4, 106, 130, 139],
            [23, 14, 138, 140, 236],
            [24, 1, 15, 16, 124, 125],
            [25, 124, 126, 141, 142, 151],
            [26, 1, 15, 16, 124, 125],
            [27, 12, 8, 29, 191],
            [28, 195, 196],
            [29, 200, 201],
            [30, 16, 23, 6, 13],
            [46, 221, 224, 556, 263],
            [61, 280, 22, 4, 346],
            [62, 8, 531, 530, 529],
            [635, 15, 14, 16, 634],
            [221, 47, 224, 556, 263],
            [224, 221, 47, 556, 263],
            [239, 243, 242, 9],
            [242, 1, 242],
            [243, 1, 9],
            [263, 221, 47, 224, 556],
            [281, 22, 4, 346, 61],
            [346, 280, 22, 4, 61],
            [528, 62, 530],
            [529, 8, 531],
            [530, 531, 529],
            [531, 62, 8, 529],
            [545, 549, 615, 618],
            [549, 615, 545, 618],
            [556, 221, 47, 224, 263],
            [559, 562, 560, 563, 573],
            [560, 559, 562, 563, 573],
            [562, 559, 560, 563, 573],
            [563, 559, 562, 560, 573],
            [573, 560, 563],
            [578, 615, 549, 545],
            [615, 549, 545, 615, 618],
            [634, 15, 14, 16, 635]
        ]
  
        # --- GENERATION PARAMETERS ---
        NUM_DUMMY_USERS = 50
        NUM_ORDERS_TO_CREATE = 2000

        # --- HELPER FUNCTIONS ---
        def generate_unique_username(first_name, last_name):
            """Generate unique creative usernames"""
            styles = [
                f"{first_name.lower()}{random.randint(100, 9999)}",
                f"{first_name.lower()}_{last_name.lower()}",
                f"{first_name.lower()}.{last_name.lower()}",
                f"{last_name.lower()}{first_name[0].lower()}{random.randint(10, 99)}",
                f"{first_name[:3].lower()}{last_name[:3].lower()}{random.randint(1000, 9999)}",
                f"{''.join(random.choices(['cool', 'super', 'pro', 'the', 'real'], k=1))}{first_name.lower()}",
            ]
            return random.choice(styles)
        
        def generate_email(first_name, last_name):
            """Generate realistic email addresses with Indian domains"""
            domains = ['gmail.com', 'yahoo.co.in', 'outlook.com', 'hotmail.com', 'yahoo.com']
            styles = [
                f"{first_name.lower()}.{last_name.lower()}",
                f"{first_name.lower()}{last_name.lower()}",
                f"{first_name.lower()}{random.randint(100, 9999)}",
                f"{first_name[0].lower()}{last_name.lower()}",
                f"{first_name.lower()}_{last_name.lower()}",
            ]
            return f"{random.choice(styles)}@{random.choice(domains)}"
        
        def generate_indian_phone():
            """Generate realistic Indian mobile numbers"""
            # Indian mobile numbers start with 6, 7, 8, or 9
            return int(f"{random.choice([6, 7, 8, 9])}{random.randint(100000000, 999999999)}")
        
        def calculate_gst(subtotal):
            """Calculate GST based on order value"""
            if subtotal <= 1000:
                return subtotal * Decimal('0.05')
            else:
                return subtotal * Decimal('0.12')
        
        def generate_payment_id():
            """Generate a guaranteed unique payment ID using UUID."""
            # This is robust and will not create duplicates.
            return f"PAY_{uuid.uuid4().hex[:16]}"

        # --- GENERATE REALISTIC USERS ---
        self.stdout.write(f"Generating {NUM_DUMMY_USERS} realistic users and addresses...")
        users = []
        for i in range(NUM_DUMMY_USERS):
            first_name = fake.first_name()
            last_name = fake.last_name()
            
            # Generate unique DOB for each user
            user_dob = fake.date_of_birth(minimum_age=18, maximum_age=65)
            user_username = generate_unique_username(first_name, last_name)
            user_email = generate_email(first_name, last_name)
            user_contact = generate_indian_phone()  # Use Indian phone generator
            
            user, created = User.objects.get_or_create(
                email=user_email,
                defaults={
                    'username': user_username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'password': 'password123',
                    'date_of_birth': user_dob,
                    'contact': user_contact,
                    'gender': random.choice(['male', 'female'])
                }
            )
            users.append(user)

            if not User_Address.objects.filter(user_id=user).exists():
                # Generate realistic Indian secondary address
                secondary_addresses = [
                    '', 
                    f"Flat {random.randint(1, 50)}, Building {random.randint(1, 20)}",
                    f"Apartment {random.randint(101, 999)}",
                    f"Floor {random.randint(1, 15)}, Wing {random.choice(['A', 'B', 'C'])}",
                    f"Near {fake.street_name()}",
                ]
                
                User_Address.objects.create(
                    user_id=user,
                    address_type=random.choice(['home', 'work', 'other']),
                    address_name=random.choice(["Home", "Work", "My Place", "Office", "Apartment"]),
                    full_name=f"{first_name} {last_name}",
                    phone=user_contact,
                    address_line_1=fake.street_address(),
                    address_line_2=random.choice(secondary_addresses),
                    city=fake.city(),
                    state=fake.state(),
                    pincode=fake.postcode(),
                    is_default=True
                )
        
        # --- FETCH PRODUCT VARIANTS ---
        self.stdout.write("Fetching product variants for order creation...")
        all_variants = list(Product_Variants.objects.filter(is_active=True, product_id__is_active=True))
        if not all_variants:
            self.stdout.write(self.style.ERROR("No active Product Variants found."))
            return
        
        product_to_variants_map = {p.id: [] for p in Product.objects.all()}
        for variant in all_variants:
            product_to_variants_map[variant.product_id_id].append(variant)

        # --- GENERATE REALISTIC ORDERS ---
        self.stdout.write(f"Generating {NUM_ORDERS_TO_CREATE} orders with realistic data...")
        for i in range(NUM_ORDERS_TO_CREATE):
            try:
                with transaction.atomic():
                    order_user = random.choice(users)
                    user_default_address = User_Address.objects.filter(user_id=order_user, is_default=True).first()
                    if not user_default_address:
                        continue

                    # --- BUILD SMART CART ---
                    cart_variants = []
                    chosen_cluster = random.choice(PRODUCT_CLUSTERS)
                    num_themed_items = random.randint(2, min(3, len(chosen_cluster)))
                    themed_product_ids = random.sample(chosen_cluster, num_themed_items)
                    
                    for pid in themed_product_ids:
                        if pid in product_to_variants_map and product_to_variants_map[pid]:
                            variant = random.choice(product_to_variants_map[pid])
                            if variant not in cart_variants:
                                cart_variants.append(variant)
                    
                    num_random_items = random.randint(0, 2)
                    for _ in range(num_random_items):
                        variant = random.choice(all_variants)
                        if variant not in cart_variants:
                            cart_variants.append(variant)
                    
                    if not cart_variants:
                        continue
                    
                    # --- CALCULATE ORDER TOTALS ---
                    order_details = []
                    subtotal = Decimal('0.00')
                    
                    for v in cart_variants:
                        quantity = random.randint(1, 3)
                        unit_price = v.product_id.price + (v.additional_price or Decimal('0'))
                        total_price = unit_price * quantity
                        subtotal += total_price
                        
                        order_details.append(Order_Details(
                            product_variant_id=v,
                            quantity=quantity,
                            unit_price=unit_price,
                            total_price=total_price,
                            product_name=v.product_id.name,
                            product_sku=v.sku
                        ))

                    # Calculate taxes and shipping
                    tax_amount = calculate_gst(subtotal)
                    shipping_charge = Decimal('69.00')
                    total_amount = subtotal + shipping_charge  # Tax is inclusive
                    
                    # Generate historical order date
                    order_datetime = fake.date_time_between(start_date='-2y', end_date='now', tzinfo=timezone.get_current_timezone())
                    
                    # Determine order status
                    order_status = random.choices(
                        ['delivered', 'shipped', 'confirmed', 'processing'],
                        weights=[70, 15, 10, 5],
                        k=1
                    )[0]
                    
                    # Payment method
                    payment_method = random.choice(['cod', 'card', 'upi'])
                    
                    # Expected delivery (5-7 days from order date)
                    expected_delivery_date = (order_datetime + timedelta(days=random.randint(5, 7))).date()
                    
                    # --- CREATE ORDER ---
                    order = Order_Master.objects.create(
                        user_id=order_user,
                        status=order_status,
                        mode_of_payment=payment_method,
                        subtotal=subtotal,
                        tax_amount=tax_amount,
                        shipping_charge=shipping_charge,
                        total_amount=total_amount,
                        expected_delivery=expected_delivery_date,
                        created_at=order_datetime,
                        order_date=order_datetime
                    )
                    
                    # Update timestamps
                    Order_Master.objects.filter(pk=order.pk).update(
                        created_at=order_datetime,
                        order_date=order_datetime
                    )
                    
                    # --- CREATE ORDER DETAILS ---
                    for detail in order_details:
                        detail.order_id = order
                    Order_Details.objects.bulk_create(order_details)

                    # --- CREATE ORDER ADDRESS ---
                    Order_Address.objects.create(
                        order_id=order,
                        address_type=user_default_address.address_type,
                        full_name=user_default_address.full_name,
                        phone=user_default_address.phone,
                        address_line_1=user_default_address.address_line_1,
                        address_line_2=user_default_address.address_line_2,
                        city=user_default_address.city,
                        state=user_default_address.state,
                        pincode=user_default_address.pincode,
                    )
                    
                    # --- CREATE SHIPPING RECORD ---
                    shipping_status_map = {
                        'processing': 'confirm',
                        'confirmed': 'confirm',
                        'shipped': 'shipped',
                        'delivered': 'delivered',
                    }
                    shipping_status = shipping_status_map.get(order_status, 'confirm')
                    
                    shipped_date = None
                    delivered_date = None
                    
                    if shipping_status == 'shipped':
                        shipped_date = order_datetime + timedelta(days=random.randint(1, 3))
                    elif shipping_status == 'delivered':
                        shipped_date = order_datetime + timedelta(days=random.randint(1, 3))
                        delivered_date = shipped_date + timedelta(days=random.randint(2, 5))
                    
                    Shipping.objects.create(
                        order_id=order,
                        shipping_status=shipping_status,
                        shipped_date=shipped_date,
                        excepted_delivery=expected_delivery_date,
                        delivered_date=delivered_date,
                        delivery_notes=fake.sentence() if random.random() > 0.7 else None,
                        created_at=order_datetime
                    )
                    
                    # --- CREATE PAYMENT RECORD ---
                    payment_status = 'completed' if payment_method == 'cod' or order_status in ['delivered', 'shipped'] else 'pending'
                    
                    gateway_mapping = {
                        'cod': 'COD',
                        'card': 'Razorpay',
                        'upi': 'Razorpay'
                    }
                    
                    payment = Payment.objects.create(
                        payment_id=generate_payment_id(),
                        order_id=order,
                        user_id=order_user,
                        amount=total_amount,
                        payment_method=payment_method,
                        payment_gateway=gateway_mapping[payment_method],
                        gateway_order_id=f"order_{random.randint(100000, 999999)}" if payment_method != 'cod' else None,
                        gateway_payment_id=f"pay_{random.randint(100000, 999999)}" if payment_method != 'cod' and payment_status == 'completed' else None,
                        gateway_signature=''.join(random.choices(string.ascii_letters + string.digits, k=40)) if payment_method != 'cod' and payment_status == 'completed' else None,
                        status=payment_status,
                        transaction_date=order_datetime,
                        created_at=order_datetime
                    )
                    
                    if (i + 1) % 100 == 0:
                        self.stdout.write(f"  ... {i+1}/{NUM_ORDERS_TO_CREATE} orders created.")
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating order {i+1}: {e}"))

        self.stdout.write(self.style.SUCCESS("✅ Enhanced seeding complete! Database populated with realistic data."))