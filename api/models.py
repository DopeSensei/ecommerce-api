import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.utils.text import slugify

# Create your models here.

class User(AbstractUser):
    email = models.EmailField(unique=True)

class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField()
    image = models.ImageField(upload_to='products/', blank=True, null=True)

    category = models.ForeignKey(
        "Category",
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        blank=True,
        )


    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def in_stock(self):
        return self.stock > 0
    
    def reduce_stock(self, amount=1):
        if amount < 1:
            raise ValueError("amount must be >= 1")
        if self.stock < amount:
            raise ValueError("insufficient stock")
        self.stock -= amount
        self.save(update_fields=["stock"])
    
    # Handles discount logic
    def get_effective_price(self):
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price
    
    # Auto-generate a unique slug from product name for clean/stable URLs.
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 2

            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)
    
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
        SHIPPED = 'Shipped'
        CONFIRMED = 'Confirmed'
        DELIVERED = 'Delivered'
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

    def calculate_total(self):
        total = sum((item.item_subtotal for item in self.items.all()), Decimal("0.00"))
        self.total_price = total
        self.save(update_fields=["total_price"])
        return total

    def mark_as_paid(self):
        self.payment_status = "paid"
        self.save(update_fields=["payment_status"])

    def __str__(self):
        username = self.user.username if self.user else "delete-user"
        return f"Order {self.order_id} by {username}"
    

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    # Keep product rows for accounting/audit consistency on old order items.
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    # Every order item must store a purchase-time price for reliable financial history.
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, null=False, blank=False)

    @property
    def item_subtotal(self):
        return self.price_at_purchase * self.quantity
    
    # Total order price should not be affected even if the product price changes afterwards.
    def save(self, *args, **kwargs):
        if self.price_at_purchase is None:
            self.price_at_purchase = self.product.get_effective_price()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.order_id}"
    

class Cart(models.Model):
    # Prevent multiple carts per user
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_total(self):
        return sum((item.get_total_price() for item in self.items.select_related("product")), Decimal("0.00"))
    

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevents duplicate rows for the same product in a single cart.
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="unique_cart_product")
        ]

    def get_total_price(self):
        return self.product.get_effective_price() * self.quantity
    

class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True) # URL-friendly identifier (e.g., coffee-machine-pro); unique=True keeps each category slug distinct.
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"] # Category queries such as Category.objects.all() are ordered by name by default.

    # Auto-fills slug from name when it is left blank.
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
