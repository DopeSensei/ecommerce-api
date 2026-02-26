import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# Create your models here.

class User(AbstractUser):
    pass

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    image = models.ImageField(upload_to='products/', blank=True, null=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def in_stock(self):
        return self.stock > 0
    
    def __str__(self):
        return self.name
    

class Address(models.Model):
    # Use AUTH_USER_MODEL so this relation stays valid with custom user models.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, blank=True)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="Turkey")
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} - {self.city}"
    

class Order(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'Pending'
        CONFIRMED = 'Confirmed'
        CANCELLED = 'Cancelled'

    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    # Keep order history if a user account is deleted.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.PENDING)

    products = models.ManyToManyField(Product, through="OrderItem", related_name='orders')

    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Prevent address deletion while it is referenced by an order.
    shipping_address = models.ForeignKey("Address", on_delete=models.PROTECT, related_name="shipping_orders")
    billing_address = models.ForeignKey("Address", on_delete=models.PROTECT, related_name="billing_orders")

    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("unpaid", "Unpaid"),
            ("paid", "Paid"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
        ],
        default="unpaid"
    )

    payment_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        username = self.user.username if self.user else "delete-user"
        return f"Order {self.order_id} by {username}"
    

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    # Keep product rows for accounting/audit consistency on old order items.
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    @property
    def item_subtotal(self):
        return self.product.price * self.quantity
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.order_id}"
