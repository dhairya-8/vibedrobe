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

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.username