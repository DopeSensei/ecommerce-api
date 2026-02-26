from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Product, Address, Order, OrderItem

# Register your models here.

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    pass

admin.site.register(Product)
admin.site.register(Address)
admin.site.register(Order)
admin.site.register(OrderItem)