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
    profile_image = models.ImageField(upload_to='admin_profile_pictures/', null=True, blank=True)
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

    def _str_(self):
        return self.username
    
class User(models.Model):
    email = models.EmailField(unique=True,null=False, blank=False,max_length=100)
    username = models.CharField(max_length=50, unique=True,null=False, blank=False)
    password = models.CharField(max_length=255, null=False, blank=False)
    first_name = models.CharField(max_length=50, null=False, blank=False)
    last_name = models.CharField(max_length=50, null=False, blank=False)
    contact = models.BigIntegerField(null=False, blank=False)
    date_of_birth = models.DateField(null=False, blank=False)
    gender = models.CharField(max_length=20, choices=[('1', 'Female'), ('2', 'Male')])
    profile_image = models.ImageField(upload_to='user_profile_pictures/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=True)
    registration_date = models.DateField(null=False, blank=False)
    last_login = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def _str_(self):
        return self.username

class User_Address(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    address_type = models.CharField(max_length=20, null=False, blank=False)
    full_name = models.CharField(max_length=100, null=False, blank=False)
    phone = models.BigIntegerField(null=False, blank=False)
    address_line_1 = models.CharField(max_length=200, null=False, blank=False)
    address_line_2 = models.CharField(max_length=200, null=False, blank=False)
    city = models.CharField(max_length=50, null=False, blank=False)
    state = models.CharField(max_length=50, null=False, blank=False)
    pincode = models.CharField(max_length=10, null=False, blank=False)
    country = models.CharField(max_length=200, null=False, blank=False)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def _str_(self):
        return self.full_name
    
class Category(models.Model):
    name = models.CharField(max_length=50, unique=True,null=False, blank=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(null=False, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def _str_(self):
        return self.name

class Sub_Category(models.Model):
    category_id = models.ForeignKey(Category, on_delete=models.CASCADE,related_name='subcategories')
    name = models.CharField(max_length=50, unique=True,null=False, blank=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(null=False, default=0)
    
    def _str_(self):
        return self.name

class Brand(models.Model):
    name = models.CharField(max_length=50, unique=True,null=False, blank=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def _str_(self):
        return self.name
    
class Size(models.Model):
    name = models.CharField(max_length=50, unique=True,null=False, blank=False)
    sort_order = models.IntegerField(null=False, default=0)
    is_active = models.BooleanField(default=True)
    
    def _str_(self):
        return self.name

class Material(models.Model):
    name = models.CharField(max_length=50, unique=True,null=False, blank=False)
    description = models.TextField(max_length=200, null=False, blank=False)
    is_active = models.BooleanField(default=True)
    
    def _str_(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200, unique=True,null=False, blank=False)
    description = models.TextField(max_length=2000, null=False, blank=False)
    price = models.DecimalField(decimal_places=2,max_digits=10, null=False, blank=False)
    base_image = models.TextField(max_length=300, null=False, blank=False)
    subcategory_id = models.ForeignKey(Sub_Category, on_delete=models.CASCADE)
    brand_id = models.ForeignKey(Brand, on_delete=models.CASCADE)
    color = models.CharField(max_length=15, null=False, blank=False)
    material_id = models.ForeignKey(Material, on_delete=models.CASCADE)
    gender = models.CharField(max_length=10, null=False, blank=False)
    sku = models.CharField(max_length=50, unique=True,null=False, blank=False)
    weight = models.DecimalField(decimal_places=2, max_digits=5, null=True)
    dimensions = models.CharField(max_length=50, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class Product_Variants(models.Model):
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size_id = models.ForeignKey(Size, on_delete=models.CASCADE)
    sku = models.CharField(max_length=50, unique=True,null=False, blank=False)
    stock_quantity = models.IntegerField(null=False,blank=False, default=0)
    reserved_quantity = models.IntegerField(default=0)
    additional_price = models.DecimalField(decimal_places=2,max_digits=8, null=True, default=0)
    is_active = models.BooleanField(default=True)
    
class Product_Gallery(models.Model):
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    image_path = models.TextField(max_length=300, null=False, blank=False)
    image_order = models.IntegerField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
class Product_Tags(models.Model):
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    tag = models.TextField(max_length=50, null=False, blank=False)
    
class Cart(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Cart_Items(models.Model):
    cart_id = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product_variant_id = models.ForeignKey(Product_Variants, on_delete=models.CASCADE)
    quantity = models.IntegerField(null=False, blank=False, default=1)
    price_at_time = models.DecimalField(decimal_places=2, max_digits=10, null=False, blank=False)
    added_at = models.DateTimeField(auto_now_add=True)
    
class Wishlist(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

class Order_Master(models.Model):
    order_number = models.CharField(max_length=20, unique=True,null=False, blank=False)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=25, null=False, blank=False)
    subtotal = models.DecimalField(decimal_places=2, max_digits=10, null=False, blank=False)
    tax_amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    shipping_charge = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    total_amount = models.DecimalField(decimal_places=2,max_digits=10, null=False, blank=False)
    order_date = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class Order_Details(models.Model):
    order_id = models.ForeignKey(Order_Master, on_delete=models.CASCADE)
    product_variant_id = models.ForeignKey(Product_Variants, on_delete=models.CASCADE)
    quantity = models.IntegerField(null=False, blank=False)
    unit_price = models.DecimalField(decimal_places=2, max_digits=10, null=False, blank=False )
    total_price = models.DecimalField(decimal_places=2,max_digits=10, null=False, blank=False)
    product_name = models.CharField(max_length=200, null=False, blank=False)
    product_sku = models.CharField(max_length=50, null=False, blank=False)
    
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
    
class Shipping_Partners(models.Model):
    name = models.CharField(max_length=50, unique=True,null=False, blank=False)
    code = models.CharField(max_length=20, null=False, blank=False)
    api_endpoint = models.CharField(max_length=200, null=True)
    is_active = models.BooleanField(default=True)
    base_rate = models.DecimalField(decimal_places=2,max_digits=8, default=0)

class Shipping(models.Model):
    order_id = models.ForeignKey(Order_Master, on_delete=models.CASCADE)
    shipping_partners_id = models.ForeignKey(Shipping_Partners, on_delete=models.CASCADE)
    tracking_number = models.CharField(max_length=50, unique=True,null=True)
    shipping_status = models.CharField(max_length=30, null=False, blank=False)
    shipped_date = models.DateTimeField(null=True)
    excepted_delivery = models.DateField(null=True)
    delivered_date = models.DateTimeField(null=True)
    delivery_notes = models.TextField(max_length=300, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class ML_Feature_Vectors(models.Model):
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE, unique=True)
    feature_vector = models.JSONField(null=False, blank=False)
    model_name = models.CharField(max_length=50, null=False, blank=False)
    model_version = models.CharField(max_length=20, null=False, blank=False)
    vector_length = models.IntegerField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class Frequently_Bought_Together(models.Model):
    product_a_id = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="fbt_a")
    product_b_id = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="fbt_b")
    frequency_count = models.IntegerField(null=False, blank=False, default=1)
    confidence_score = models.DecimalField(decimal_places=4,max_digits=5, null=False, blank=False)
    support_score = models.DecimalField(decimal_places=4,max_digits=5, null=False, blank=False)
    lift_score = models.DecimalField(decimal_places=4, max_digits=5, null=False, blank=False)
    last_calculated = models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    order_id = models.ForeignKey(Order_Master, on_delete=models.CASCADE)
    rating = models.IntegerField(null=False, blank=False)
    title = models.CharField(max_length=100, null=True)
    comment = models.TextField(max_length=1000, null=True)
    created_at = models.DateTimeField(auto_now_add=True)