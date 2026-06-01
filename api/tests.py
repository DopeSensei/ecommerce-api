from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from api.models import Address, Cart, CartItem, Order, OrderItem, Product

# Create your tests here.

User = get_user_model()


class CheckoutFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="testpass123",
        )
        self.address = Address.objects.create(
            user=self.user,
            full_name="Customer User",
            line1="Test Street 1",
            city="Istanbul",
            postal_code="34000",
            country="Turkey",
        )
        self.product = Product.objects.create(
            name="Test Product",
            description="Test description",
            price=Decimal("100.00"),
            stock=10,
        )
        self.cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
        )

    def test_checkout_creates_order_reduces_stock_and_clears_cart(self):
        # For now, we use force_authenticate() instead of testing the JWT token flow.
        # The goal here is to test the business logic, not the authentication system.
        self.client.force_authenticate(user=self.user)

        # requests.post() sends a real HTTP request.
        # On the other hand, 
        # self.client.post() creates a test request in a Django test environment.
        response = self.client.post(
            "/api/checkout/",
            {
                "shipping_address": self.address.id,
                "billing_address": self.address.id,
            },
            format="json",
        )
        
        # Does the response status code equal HTTP 201 Created?
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.product.refresh_from_db()
        self.cart.refresh_from_db()

        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)
        self.assertEqual(self.product.stock, 8)
        self.assertFalse(self.cart.items.exists())

        order = Order.objects.get(user=self.user)
        self.assertEqual(order.shipping_address_snapshot["city"], "Istanbul")
        self.assertEqual(order.billing_address_snapshot["city"], "Istanbul")

    def test_checkout_rejects_address_owned_by_another_user(self):
        other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="testpass123",
        )
        other_address = Address.objects.create(
            user=other_user,
            full_name="Other User",
            line1="other Street 1",
            city="Ankara",
            postal_code="06000",
            country="Turkey",
        )

        # Real user logs in.
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/checkout/",
            {
                # create an order with an address that doesn't belong to the real user.
                "shipping_address": other_address.id,
                "billing_address": self.address.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)


class CartValidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="testpass123",
        )
        self.product = Product.objects.create(
            name="Limited Product",
            description="Test description",
            price=Decimal("50.00"),
            stock=3,
        )
    
    def test_cart_item_quantity_cannot_exceed_stock_on_create(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/cart/items/",
            {
                "product": self.product.id,
                "quantity": 4,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cart_item_quantity_cannot_exceed_stock_on_update(self):
        self.client.force_authenticate(user=self.user)

        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
        )

        # Update the cart item quantity to 4.
        response = self.client.patch(
            f"/api/cart/items/{cart_item.id}/",
            {
                "quantity": 4,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OrderPermissionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="testpass123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="testpass123",
        )
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
        )

        self.address = Address.objects.create(
            user=self.user,
            full_name="Customer User",
            line1="Test Street 1",
            city="Istanbul",
            postal_code="34000",
            country="Turkey",
        )
        self.other_address = Address.objects.create(
            user=self.other_user,
            full_name="Other User",
            line1="Other Street 1",
            city="Ankara",
            postal_code="06000",
            country="Turkey",
        )

        self.user_order = Order.objects.create(
            user=self.user,
            shipping_address=self.address,
            billing_address=self.address,
            shipping_address_snapshot=self.address.to_snapshot(),
            billing_address_snapshot=self.address.to_snapshot(),
        )

        self.other_order = Order.objects.create(
            user=self.other_user,
            shipping_address=self.other_address,
            billing_address=self.other_address,
            shipping_address_snapshot=self.other_address.to_snapshot(),
            billing_address_snapshot=self.other_address.to_snapshot(),
        )

    def test_unauthenticated_user_cannot_list_orders(self):
        response = self.client.get("/api/orders/")

        # Check that the response status code is either 401 or 403.
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_user_can_only_list_own_orders(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/orders/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["order_id"], str(self.user_order.order_id))

    def test_regular_user_cannot_update_order_status(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f"/api/orders/{self.user_order.order_id}/status/",
            {
                "status": Order.StatusChoices.CANCELLED,
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_order_status(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            f"/api/orders/{self.user_order.order_id}/status/",
            {
                "status": Order.StatusChoices.CANCELLED,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class InventoryRestoreTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="testpass123",
        )
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
        )
        self.address = Address.objects.create(
            user=self.user,
            full_name="Customer User",
            line1="Test Street1",
            city="Istanbul",
            postal_code="34000",
            country="Turkey",
        )
        self.product = Product.objects.create(
            name="Restock Product",
            description="Test description",
            price=Decimal("100.00"),
            stock=8,
        )
        self.order = Order.objects.create(
            user=self.user,
            shipping_address=self.address,
            billing_address=self.address,
            shipping_address_snapshot=self.address.to_snapshot(),
            billing_address_snapshot=self.address.to_snapshot(),
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
        )

    def test_cancelled_order_restores_stock(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            f"/api/orders/{self.order.order_id}/status/",
            {"status": Order.StatusChoices.CANCELLED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.product.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.product.stock, 10)
        self.assertTrue(self.order.stock_restored)

    def test_payment_failed_restores_stock(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            f"/api/orders/{self.order.order_id}/payment/",
            {
                "payment_status": "failed",
                "payment_id": "payment-test-123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.product.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.product.stock, 10)
        self.assertTrue(self.order.stock_restored)

    def test_stock_is_not_restored_twice(self):
        self.client.force_authenticate(user=self.admin)

        self.client.patch(
            f"/api/orders/{self.order.order_id}/status/",
            {"status": Order.StatusChoices.CANCELLED},
            format="json",
        )

        self.client.patch(
            f"/api/orders/{self.order.order_id}/status/",
            {"status": Order.StatusChoices.CANCELLED},
            format="json",
        )

        self.product.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.product.stock, 10)
        self.assertTrue(self.order.stock_restored)

    
class ProductVisibilityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="testpass123",
        )
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
        )
        self.inactive_product = Product.objects.create(
            name="Inactive Product",
            description="Hidden product",
            price=Decimal("25.00"),
            stock=5,
            is_active=False,
        )

    def test_inactive_product_cannot_be_added_to_cart(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/cart/items/",
            {
                "product": self.inactive_product.id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_public_user_cannot_retrieve_inactive_product(self):
        response = self.client.get(f"/api/products/{self.inactive_product.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_retrieve_inactive_product(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(f"/api/products/{self.inactive_product.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class JWTAuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jwtuser",
            email="jwt@example.com",
            password="testpass123",
        )

    def test_token_endpoint_returns_access_and_refresh_tokens(self):
        response = self.client.post(
            "/api/token/",
            {
                "username": "jwtuser",
                "password": "testpass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)