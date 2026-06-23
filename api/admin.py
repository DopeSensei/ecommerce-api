from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Product, Address, Order, OrderItem, Category, Cart, CartItem

# Register your models here.

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    pass

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "discount_price", "stock", "is_active", "category")
    search_fields = ("name", "description")
    list_filter = ("is_active", "category")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "status", "payment_status", 'total_price', "created_at")
    search_fields = ("order_id", "user__username", "user__email", "payment_id")
    list_filter = ("status", "payment_status", "created_at")

admin.site.register(Address)
admin.site.register(OrderItem)
admin.site.register(Category)
admin.site.register(Cart)
admin.site.register(CartItem)