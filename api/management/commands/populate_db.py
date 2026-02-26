# api/management/commands/populate_db.py
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import lorem_ipsum

from api.models import User, Product, Address, Order, OrderItem


class Command(BaseCommand):
    help = "Create sample data for development"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        user, created = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@example.com"},
        )
        if created:
            user.set_password("test12345")
            user.is_staff = True
            user.is_superuser = True
            user.save()

        address, _ = Address.objects.get_or_create(
            user=user,
            line1="Test Mah. 1",
            city="Istanbul",
            postal_code="34000",
            defaults={
                "full_name": "Admin User",
                "phone": "5550000000",
                "country": "Turkey",
            },
        )

        product_data = [
            ("A Scanner Darkly", "12.99", 4),
            ("Coffee Machine", "70.99", 6),
            ("Velvet Underground & Nico", "15.99", 11),
            ("Enter the Wu-Tang (36 Chambers)", "17.99", 2),
            ("Digital Camera", "350.99", 4),
            ("Watch", "500.05", 0),
        ]

        products = []
        for name, price, stock in product_data:
            p, _ = Product.objects.get_or_create(
                name=name,
                defaults={
                    "description": lorem_ipsum.paragraph(),
                    "price": Decimal(price),
                    "stock": stock,
                },
            )
            products.append(p)

        for _ in range(3):
            order = Order.objects.create(
                user=user,
                shipping_address=address,
                billing_address=address,
                payment_status="unpaid",
            )

            selected = random.sample(products, 2)
            total = Decimal("0.00")

            for product in selected:
                qty = random.randint(1, 3)
                OrderItem.objects.create(order=order, product=product, quantity=qty)
                total += product.price * qty

            order.total_price = total
            order.save(update_fields=["total_price"])

        self.stdout.write(self.style.SUCCESS("Sample data created."))
