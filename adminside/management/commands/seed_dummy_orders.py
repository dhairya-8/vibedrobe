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
            [453, 6, 94, 262],
            [104, 182, 339],
            [259, 92, 337],
            [565, 50, 92],
            [462, 259, 650, 91],
            [227, 261, 583, 90],
            [258, 6, 308, 345],
            [563, 228, 94],
            [90, 584, 95, 343],
            [181, 259, 578, 6],
            [156, 45, 261, 89],
            [301, 190, 258],
            [173, 104, 91, 105],
            [162, 235, 258],
            [89, 253, 261, 559],
            [262, 140, 118],
            [261, 303, 89],
            [618, 560, 92, 177],
            [6, 363, 580],
            [262, 88, 6],
            [344, 393, 6],
            [104, 57, 259],
            [600, 154, 6],
            [301, 6, 133, 259],
            [261, 33, 244],
            [581, 325, 104],
            [259, 330, 91],
            [92, 94, 320],
            [46, 259, 573, 92],
            [473, 260, 564, 6]
        ]
    
        # --- GENERATION PARAMETERS ---
        NUM_DUMMY_USERS = 50
        NUM_ORDERS_TO_CREATE = 2000
        # --- NEW: SET YOUR BIAS HERE ---
        # 75% of orders will be "Cluster Orders" to create strong patterns
        CLUSTER_ORDER_BIAS = 0.75 

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
            return int(f"{random.choice([6, 7, 8, 9])}{random.randint(100000000, 999999999)}")
        
        def calculate_gst(subtotal):
            """Calculate GST based on order value"""
            if subtotal <= 1000:
                return subtotal * Decimal('0.05')
            else:
                return subtotal * Decimal('0.12')
        
        def generate_payment_id():
            """Generate a guaranteed unique payment ID using UUID."""
            return f"PAY_{uuid.uuid4().hex[:16]}"

        # --- GENERATE REALISTIC USERS ---
        self.stdout.write(f"Generating {NUM_DUMMY_USERS} realistic users and addresses...")
        users = []
        for i in range(NUM_DUMMY_USERS):
            first_name = fake.first_name()
            last_name = fake.last_name()
            
            user_dob = fake.date_of_birth(minimum_age=18, maximum_age=65)
            user_username = generate_unique_username(first_name, last_name)
            user_email = generate_email(first_name, last_name)
            user_contact = generate_indian_phone() 
            
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
            # Ensure product_id_id exists in the map before appending
            if variant.product_id_id in product_to_variants_map:
                product_to_variants_map[variant.product_id_id].append(variant)

        # --- GENERATE REALISTIC ORDERS ---
        self.stdout.write(f"Generating {NUM_ORDERS_TO_CREATE} orders with realistic data...")
        orders_created = 0
        cluster_orders_created = 0
        random_orders_created = 0

        for i in range(NUM_ORDERS_TO_CREATE):
            try:
                with transaction.atomic():
                    order_user = random.choice(users)
                    user_default_address = User_Address.objects.filter(user_id=order_user, is_default=True).first()
                    if not user_default_address:
                        continue

                    # ######################################################
                    # ### --- MODIFIED: BUILD SMART CART --- ###
                    # ######################################################
                    
                    cart_variants = []
                    
                    if random.random() < CLUSTER_ORDER_BIAS:
                        # --- This is a "Cluster Order" ---
                        # We will *force* items from a cluster to be bought together
                        chosen_cluster = random.choice(PRODUCT_CLUSTERS)
                        
                        # Pick a "strong" number of items from the cluster
                        min_items = 2
                        max_items = min(4, len(chosen_cluster)) # Pick up to 4 items or cluster size
                        if max_items < min_items:
                             max_items = min_items # ensure we pick at least 2 if cluster is tiny

                        num_themed_items = random.randint(min_items, max_items)
                        themed_product_ids = random.sample(chosen_cluster, num_themed_items)
                        
                        for pid in themed_product_ids:
                            # Check if product ID is valid and has variants
                            if pid in product_to_variants_map and product_to_variants_map[pid]:
                                variant = random.choice(product_to_variants_map[pid])
                                if variant not in cart_variants:
                                    cart_variants.append(variant)
                        
                        # Add a *small* chance of 1 random item to add a little noise
                        if random.random() < 0.25: # 25% chance of adding one random item
                             variant = random.choice(all_variants)
                             if variant not in cart_variants:
                                 cart_variants.append(variant)
                        
                        if cart_variants:
                            cluster_orders_created += 1

                    else:
                        # --- This is a "Random Order" ---
                        # These orders create the "background noise"
                        # We must ensure they have at least 2 items to be analyzed by FBT
                        num_random_items = random.randint(2, 5) 
                        
                        for _ in range(num_random_items):
                            variant = random.choice(all_variants)
                            if variant not in cart_variants:
                                cart_variants.append(variant)
                        
                        if cart_variants:
                            random_orders_created += 1
                    
                    # ######################################################
                    # ### --- END OF MODIFICATIONS --- ###
                    # ######################################################
                    
                    if not cart_variants:
                        continue
                    
                    # --- CALCULATE ORDER TOTALS ---
                    order_details = []
                    subtotal = Decimal('0.00')
                    
                    for v in cart_variants:
                        quantity = random.randint(1, 3)
                        # Handle potential None for additional_price
                        additional_price = v.additional_price or Decimal('0')
                        unit_price = v.product_id.price + additional_price
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
                    total_amount = subtotal + shipping_charge # Assuming tax is inclusive, adjust if not
                    
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
                        # Set created_at and order_date here directly
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
                    
                    orders_created += 1
                    if (i + 1) % 100 == 0:
                        self.stdout.write(f"   ... {i+1}/{NUM_ORDERS_TO_CREATE} loops processed ({orders_created} valid orders created).")
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating order {i+1}: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"--- Seeding Stats ---"))
        self.stdout.write(self.style.SUCCESS(f"Total Orders Created: {orders_created}"))
        self.stdout.write(self.style.SUCCESS(f"Cluster-biased Orders: {cluster_orders_created} (~{cluster_orders_created/orders_created*100:.0f}%)"))
        self.stdout.write(self.style.SUCCESS(f"Random Orders: {random_orders_created} (~{random_orders_created/orders_created*100:.0f}%)"))
        self.stdout.write(self.style.SUCCESS("✅ Enhanced seeding complete!"))