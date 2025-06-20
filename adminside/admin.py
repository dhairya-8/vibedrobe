from django.contrib import admin
from .models import *

admin.site.register(Admin)
admin.site.register(User)
admin.site.register(Order_Master)
admin.site.register(Order_Details)
admin.site.register(Order_Address)