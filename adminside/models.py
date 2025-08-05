from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

# Models for admin and user 
class Admin(models.Model):
    email = models.EmailField(unique=True,null=False, blank=False,max_length=100)
    username = models.CharField(max_length=50, unique=True,null=False, blank=False)
    password = models.CharField(max_length=255, null=False, blank=False)
    first_name = models.CharField(max_length=50, null=False, blank=False)
    last_name = models.CharField(max_length=50, null=False, blank=False)
    profile_image = models.ImageField(upload_to='adminside/admin_profile_pictures/', null=True, blank=True)
    role = models.CharField(max_length=20, choices=[('super_admin', 'Super Admin'), ('admin', 'Admin'),('moderator', 'Moderator')], default='admin')
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Hash the password only if it's not already hashed
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
        
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"Admin: {self.username} ({self.role})"
    
class User(models.Model):
    email = models.EmailField(unique=True,null=False, blank=False,max_length=100)
    username = models.CharField(max_length=50, unique=True,null=False, blank=False)
    password = models.CharField(max_length=255, null=False, blank=False)
    first_name = models.CharField(max_length=50, null=False, blank=False)
    last_name = models.CharField(max_length=50, null=False, blank=False)
    contact = models.BigIntegerField(null=False, blank=False)
    date_of_birth = models.DateField(null=False, blank=False)
    gender = models.CharField(max_length=20, choices=[('1', 'Female'), ('2', 'Male')])
    profile_image = models.ImageField(upload_to='userside/user_profile_pictures/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=True)
    registration_date = models.DateField(null=False, blank=False)
    last_login = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """Automatically hash password when saving"""
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
        
    def set_password(self, raw_password):
        """Set hashed password"""
        self.password = make_password(raw_password)
        
    def check_password(self, raw_password):
        """Verify password"""
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"User#{self.id}: {self.email}"

class User_Address(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    ADDRESS_TYPE_CHOICES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    address_type = models.CharField(max_length=20, null=False, blank=False, choices=ADDRESS_TYPE_CHOICES, default='home')
    address_name = models.CharField(max_length=80, null=False, blank=False, default='Home', help_text="Name for this address (e.g., Home, Work)")
    full_name = models.CharField(max_length=100, null=False, blank=False)
    phone = models.BigIntegerField(null=False, blank=False)
    address_line_1 = models.CharField(max_length=200, null=False, blank=False)
    address_line_2 = models.CharField(max_length=200, blank=True, default='')
    city = models.CharField(max_length=50, null=False, blank=False)
    state = models.CharField(max_length=50, null=False, blank=False)
    pincode = models.CharField(max_length=10, null=False, blank=False)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.address_name} ({self.get_address_type_display()})"

    def get_full_address(self):
        return f"{self.address_line_1}{', ' + self.address_line_2 if self.address_line_2 else ''}, {self.city}, {self.state} {self.pincode},"
    
class Category(models.Model):
    name = models.CharField(max_length=50, unique=True,null=False, blank=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(null=False, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Category: {self.name}"

class Sub_Category(models.Model):
    category_id = models.ForeignKey(Category, on_delete=models.CASCADE,related_name='subcategories')
    name = models.CharField(max_length=50, unique=True,null=False, blank=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(null=False, default=0)
    
    def __str__(self):
        return f"SubCategory: {self.name} > {self.category_id.name}"

class Brand(models.Model):
    name = models.CharField(max_length=50, unique=True,null=False, blank=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Brand: {self.name}"
    
class Size(models.Model):
    name = models.CharField(max_length=50, unique=True,null=False, blank=False)
    sort_order = models.IntegerField(null=False, default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Size: {self.name}"

class Material(models.Model):
    name = models.CharField(max_length=50, unique=True,null=False, blank=False)
    description = models.TextField(max_length=200, null=False, blank=False)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Material: {self.name[:20]}..."

class Product(models.Model):
    name = models.CharField(max_length=200,null=False, blank=False)
    description = models.TextField(max_length=2000, null=False, blank=False)
    price = models.DecimalField(decimal_places=2,max_digits=10, null=False, blank=False)
    base_image = models.ImageField(upload_to='products/base', null=True, blank=True)
    subcategory_id = models.ForeignKey(Sub_Category, on_delete=models.CASCADE)
    fit_type = models.CharField(max_length=50, blank=True, null=True)
    brand_id = models.ForeignKey(Brand, on_delete=models.CASCADE)
    color = models.CharField(max_length=50, null=False, blank=False)
    material_id = models.ForeignKey(Material, on_delete=models.CASCADE)
    gender = models.CharField(max_length=10, null=False, blank=False)
    weight = models.DecimalField(decimal_places=2, max_digits=5, null=True)
    dimensions = models.CharField(max_length=50, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Product#{self.id}: {self.name[:50]} ({self.brand_id.name})"
    
    def get_average_rating(self):
        """Returns the average rating for this product"""
        from django.db.models import Avg
        result = self.review_set.aggregate(average=Avg('rating'))
        return round(result['average'] or 0)
    
class Product_Variants(models.Model):
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size_id = models.ForeignKey(Size, on_delete=models.CASCADE)
    sku = models.CharField(max_length=50, unique=True,null=False, blank=False)
    stock_quantity = models.IntegerField(null=False,blank=False, default=0)
    reserved_quantity = models.IntegerField(default=0)
    additional_price = models.DecimalField(decimal_places=2,max_digits=8, null=True, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product_id.name} - {self.size_id.name} (SKU: {self.sku})"

    
    def first_gallery_image(self):
        """Returns the first gallery image ordered by image_order"""
        return self.product_gallery_set.order_by('image_order').first()
    
    def has_gallery_images(self):
        """Check if product has any gallery images"""
        return self.product_gallery_set.exists()

    @property
    def product(self):
        return self.product_id
        
    def get_main_image(self):
        return self.product_id.images.first()

    
class Product_Gallery(models.Model):
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    image_path = models.ImageField(upload_to='products/gallery', null=True, blank=True)
    image_order = models.IntegerField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image #{self.image_order} for {self.product_id.name}"
    
class Product_Tags(models.Model):
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    tag = models.TextField(max_length=50, null=False, blank=False)

    def __str__(self):
        return f"Tag: {self.tag[:20]}"
    
class Cart(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart#{self.id} for User#{self.user_id.id}"

class Cart_Items(models.Model):
    cart_id = models.ForeignKey(Cart, on_delete=models.PROTECT, related_name='items')
    product_variant_id = models.ForeignKey(Product_Variants, on_delete=models.CASCADE)
    quantity = models.IntegerField(null=False, blank=False, default=1)
    price_at_time = models.DecimalField(decimal_places=2, max_digits=10, null=False, blank=False)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity}x Variant#{self.product_variant_id.id}"

    @property
    def total_price(self):
        return self.price_at_time * self.quantity
        
    def __str__(self):
        return f"{self.quantity}x {self.product_variant_id.product_id.name} in Cart#{self.cart_id.id}"

    
class Wishlist(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wish: User#{self.user_id.id} > Product#{self.product_id.id}"

    @property
    def in_stock(self):
        return self.product_id.variants.filter(stock_quantity__gt=0).exists()
    
class Order_Master(models.Model):
    order_number = models.CharField(max_length=20, unique=True,null=False, blank=False)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    status = models.CharField(max_length=25, null=False, blank=False, choices=STATUS_CHOICES, default='processing')
    subtotal = models.DecimalField(decimal_places=2, max_digits=10, null=False, blank=False)
    tax_amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    shipping_charge = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    total_amount = models.DecimalField(decimal_places=2,max_digits=10, null=False, blank=False)
    order_date = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Example: ORD-20230712-0001
            date_str = timezone.now().strftime('%Y%m%d')
            last_order = Order_Master.objects.filter(order_number__contains=date_str).last()
            if last_order:
                last_num = int(last_order.order_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.order_number = f"ORD-{date_str}-{new_num:04d}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Order#{self.order_number}: ${self.total_amount} ({self.status})"
    
class Order_Details(models.Model):
    order_id = models.ForeignKey(Order_Master, on_delete=models.PROTECT)
    product_variant_id = models.ForeignKey(Product_Variants, on_delete=models.CASCADE)
    quantity = models.IntegerField(null=False, blank=False)
    unit_price = models.DecimalField(decimal_places=2, max_digits=10, null=False, blank=False )
    total_price = models.DecimalField(decimal_places=2,max_digits=10, null=False, blank=False)
    product_name = models.CharField(max_length=200, null=False, blank=False)
    product_sku = models.CharField(max_length=50, null=False, blank=False)

    def __str__(self):
        return f"{self.quantity}x {self.product_name[:20]}"
    
class Order_Address(models.Model):
    order_id = models.ForeignKey(Order_Master, on_delete=models.CASCADE)
    address_type = models.CharField(max_length=20, null=False, blank=False)
    full_name = models.CharField(max_length=100, null=False, blank=False)
    phone = models.BigIntegerField(null=False, blank=False)
    address_line_1 = models.CharField(max_length=200, null=False, blank=False)
    address_line_2 = models.CharField(max_length=200, null=False, blank=False)
    city = models.CharField(max_length=50, null=False, blank=False)
    state = models.CharField(max_length=50, null=False, blank=False)
    pincode = models.CharField(max_length=10, null=False, blank=False)
 
    def __str__(self):
        return f"Address for Order#{self.order_id.order_number}: {self.full_name} ({self.address_type})"

class Payment(models.Model):
    payment_id = models.CharField(max_length=50, unique=True,null=False, blank=False)
    order_id = models.ForeignKey(Order_Master, on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(decimal_places=2,max_digits=10, null=False, blank=False)
    payment_method = models.CharField(max_length=30, null=False, blank=False)
    payment_gateway = models.CharField(max_length=30, null=False, blank=False)
    gateway_order_id = models.CharField(max_length=100, null=True)
    gateway_payment_id = models.CharField(max_length=100, null=True)
    gateway_signature= models.CharField(max_length=200, null=True)
    status= models.CharField(max_length=20, null=False, blank=False)
    failure_reason = models.TextField(max_length=300, null=True)
    refund_amount = models.DecimalField(decimal_places=2,max_digits=10, default=0)
    refund_reason = models.TextField(max_length=300, null=True)
    transaction_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment#{self.payment_id}: {self.status} (${self.amount})"
    
class Shipping_Partners(models.Model):
    name = models.CharField(max_length=50, unique=True,null=False, blank=False)
    code = models.CharField(max_length=20, null=False, blank=False)
    api_endpoint = models.CharField(max_length=200, null=True)
    is_active = models.BooleanField(default=True)
    base_rate = models.DecimalField(decimal_places=2,max_digits=8, default=0)

    def __str__(self):
        return f"Courier: {self.name}"

class Shipping(models.Model):
    order_id = models.ForeignKey(Order_Master, on_delete=models.CASCADE)
    shipping_partners_id = models.ForeignKey(Shipping_Partners, on_delete=models.CASCADE)
    tracking_number = models.CharField(max_length=50, unique=True,null=True)
    shipping_status = models.CharField(max_length=30, null=False, blank=False) # choices to be defined after discussion
    shipped_date = models.DateTimeField(null=True)
    excepted_delivery = models.DateField(null=True)
    delivered_date = models.DateTimeField(null=True)
    delivery_notes = models.TextField(max_length=300, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ship#{self.tracking_number or 'NA'}: {self.shipping_status}"
    
class ML_Feature_Vectors(models.Model):
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE, unique=True)
    feature_vector = models.JSONField(null=False, blank=False)
    model_name = models.CharField(max_length=50, null=False, blank=False)
    model_version = models.CharField(max_length=20, null=False, blank=False)
    vector_length = models.IntegerField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ML: {self.product_id.name} ({self.model_name})"
    
class Frequently_Bought_Together(models.Model):
    product_a_id = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="fbt_a")
    product_b_id = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="fbt_b")
    frequency_count = models.IntegerField(null=False, blank=False, default=1)
    confidence_score = models.DecimalField(decimal_places=4,max_digits=5, null=False, blank=False)
    support_score = models.DecimalField(decimal_places=4,max_digits=5, null=False, blank=False)
    lift_score = models.DecimalField(decimal_places=4, max_digits=5, null=False, blank=False)
    last_calculated = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FBT: {self.product_a_id.name} + {self.product_b_id.name}"

class Review(models.Model):
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    order_id = models.ForeignKey(Order_Master, on_delete=models.CASCADE)
    rating = models.IntegerField(null=False, blank=False)
    title = models.CharField(max_length=100, null=True)
    comment = models.TextField(max_length=1000, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user_id', 'product_id') 

    def __str__(self):
        return f"Review: {self.rating}★ for {self.product_id.name}"
    
class RecentlyViewed(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_id', 'product_id')
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.user_id.username} viewed {self.product_id.name}"