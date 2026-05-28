from django.db import transaction
from rest_framework import serializers
from .models import Product, Order, OrderItem, User, Address, Cart, CartItem, Category


# USER Serializers

class UserReadSerializer(serializers.ModelSerializer):
    orders_count = serializers.SerializerMethodField()
    orders = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id", 
            "username", 
            "email", 
            "first_name",
            "last_name",
            "orders",
            "orders_count"
        )
    
    def get_orders_count(self, obj):
        return obj.orders.count()
    

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password"
        )

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return normalized_email

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = (
            "username", 
            "email", 
            "first_name",
            "last_name",
            "password",
        )

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        qs = User.objects.filter(email__iexact=normalized_email)
        if self.instance is not None:
            # Exclude current user on update so unchanged email does not fail uniqueness validation.
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        
        return normalized_email
    
    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


# CATEGORY Serializers

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            'id',
            'name',
            'slug',
            'description',
            'parent',
            'created_at'
        )
        # Slug is auto-generated in the model save() method, so clients should not send or edit it.
        read_only_fields = (
            'id',
            'slug',
            'created_at'
        )


# PRODUCT Serializers

# READ
class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    in_stock = serializers.ReadOnlyField() #Custom field

    class Meta:
        model = Product
        fields = ( #Fields to be included in the serializer output
            'id',
            'name',
            'slug',
            'category',
            'description',
            'price',
            'discount_price',
            'stock',
            'image',
            'in_stock',
            'created_at',
            'updated_at',
        )
        read_only_fields = ("id", "slug", "in_stock", "created_at", "updated_at")


# WRITE / Handle product creation and modification for seller
class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Product
        fields = (
            'name',
            'category',
            'description',
            'price',
            'discount_price',
            'stock',
            "image"
        )

    def validate(self, attrs):
        price = attrs.get("price")
        discount_price = attrs.get("discount_price")

        if self.instance:
            if price is None:
                price = self.instance.price
            if discount_price is None:
                discount_price = self.instance.discount_price

        if discount_price is not None and price is not None and discount_price > price:
            raise serializers.ValidationError(
                {"discount_price": "Discount price cannot be greater than price."}
            )
        
        return attrs


# CART Serializers

class CartItemReadSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    item_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product_id",
            "product_name",
            "product_slug",
            "quantity",
            "added_at",
            "item_total",
        )
    
    def get_item_total(self, obj):
        return obj.get_total_price()
    

class CartItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ("product", "quantity")

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value
    
    def validate(self, attrs):
        product = attrs.get("product")
        quantity = attrs.get("quantity")

        if product is not None and not product.is_active:
            raise serializers.ValidationError({"product": "This product is inactive."})
        
        if product is not None and quantity is not None and product.stock < quantity:
            raise serializers.ValidationError(
                {"quantity": f"Only {product.stock} item(s) available in stock."}
            )
        
        return attrs
    

class CartItemQuantityUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ("quantity",)

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value
    
    def validate(self, attrs):
        # On partial updates, missing fields are taken from the existing instance so stock checks still run correctly.
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", None))
        # If "product" is omitted in PATCH requests, use the existing cart item's product from self.instance.
        product = getattr(self.instance, "product", None)

        if product is not None and quantity is not None and product.stock < quantity:
            raise serializers.ValidationError(
                {"quantity": f"Only {product.stock} item(s) available in stock."}
            )
        
        return attrs


class CartSerializer(serializers.ModelSerializer):
    items = CartItemReadSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            "id",
            "items",
            "total",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_total(self, obj):
        return obj.get_total()
    


class CheckoutSerializer(serializers.Serializer):
    shipping_address = serializers.PrimaryKeyRelatedField(queryset=Address.objects.all())
    billing_address = serializers.PrimaryKeyRelatedField(queryset=Address.objects.all())

    def validate(self, attrs):
        # Get the current request so checkout can be tied to the authenticated user.
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None

        # Checkout requires a logged-in user because cart, addresses, and orders are user-owned.
        if user is None:
            raise serializers.ValidationError(("Authentication is required to checkout."))
        
        shipping_address = attrs["shipping_address"]
        billing_address = attrs["billing_address"]

        # Django automatically provides user_id for ForeignKey fields,
        # so we can compare ownership without fetching another User object.
        if shipping_address.user_id != user.id:
            raise serializers.ValidationError(
                {"shipping_address": "You can only use your own shipping address."}
            )
        
        if billing_address.user_id != user.id:
            raise serializers.ValidationError(
                {"billing_address": "You can only use your own billing address."}
            )
        
        # Fetch the user's cart with its items/products; checkout cannot continue with an empty cart.
        try:
            cart = Cart.objects.prefetch_related("items__product").get(user=user)
        except Cart.DoesNotExist:
            raise serializers.ValidationError({"cart": "Cart is empty."})
        
        cart_items = list(cart.items.all())
        if not cart_items:
            raise serializers.ValidationError({"cart": "Cart is empty."})
        
        attrs["cart"] = cart
        attrs["cart_items"] = cart_items
        return attrs
    
    def create(self, validated_data):
        # These values are validation-only helpers, not Order model fields.
        cart = validated_data.pop("cart")
        cart_items = validated_data.pop("cart_items")
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None

        # Create the order, order items, stock updates, total calculation, and cart cleanup as one DB transaction.
        with transaction.atomic():
            shipping_address = validated_data["shipping_address"]
            billing_address = validated_data["billing_address"]

            order = Order.objects.create(
                user=user,
                shipping_address_snapshot=shipping_address.to_snapshot(),
                billing_address_snapshot=billing_address.to_snapshot(),
                **validated_data,
            )

            for cart_item in cart_items:
                # Lock the product row during checkout so concurrent orders cannot oversell the same stock.
                product = Product.objects.select_for_update().get(pk=cart_item.product_id)

                if not product.is_active:
                    raise serializers.ValidationError(
                        {"product": f"{product.name} is inactive and cannot be checked out."}
                    )
                
                if product.stock < cart_item.quantity:
                    raise serializers.ValidationError(
                        {"quantity": f"Only {product.stock} item(s) available for {product.name}"}
                    )

                # Store purchase-time price so future product price changes do not affect this order.
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=cart_item.quantity,
                    price_at_purchase=product.get_effective_price(),

                )
                product.reduce_stock(cart_item.quantity)

            order.calculate_total()
            # Checkout succeeded; remove purchased items from the user's cart.
            cart.items.all().delete()

        return order
                

# ORDER Serializers

class OrderItemReadSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    # Use purchase-time snapshot price for financial consistency; avoid exposing mutable live product prices.
    item_subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            "product_id",
            "product_name",
            "product_slug",
            "quantity",
            "price_at_purchase",
            "item_subtotal",
        )

    def get_item_subtotal(self, obj):
        return obj.item_subtotal



class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemReadSerializer(many=True, read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True, allow_null=True)
    user_email = serializers.EmailField(source="user.email", read_only=True, allow_null=True)

    class Meta:
        model = Order
        fields = (
            "order_id",
            "user_id",
            "user_email",
            "status",
            "payment_status",
            "payment_id",
            "total_price",
            "shipping_address",
            "billing_address",
            "shipping_address_snapshot",
            "billing_address_snapshot",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields



# Admin
class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("status",)

    def validate_status(self, value):
        current_status = self.instance.status if self.instance else None

        locked_statuses = {
            Order.StatusChoices.DELIVERED,
            Order.StatusChoices.CANCELLED,
            }

        if current_status in locked_statuses and value != current_status:
            raise serializers.ValidationError("Finalized orders cannot change status.")

        return value
    
    # Restore stock only when the order transitions into CANCELLED.
    # If the order is already cancelled, stock must not be restored again.
    # Delivered or cancelled orders should not move back to another status.
    def update(self, instance, validated_data):
        old_status = instance.status
        new_status = validated_data.get("status", old_status)

        instance = super().update(instance, validated_data)

        if old_status != Order.StatusChoices.CANCELLED and new_status == Order.StatusChoices.CANCELLED:
            instance.restore_stock()

        return instance


# Admin/Webhook
class OrderPaymentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("payment_status", "payment_id")

    def validate_payment_id(self, value):
        if value is None:
            return None
        value = value.strip()
        return value or None
        
    def validate(self, attrs):
        current_status = self.instance.payment_status if self.instance else None
        payment_status = attrs.get("payment_status", current_status)
        payment_id = attrs.get(
            "payment_id",
            self.instance.payment_id if self.instance else None
        )

        # Payment reference should exist for paid/refunded/failed states.
        if payment_status in {"paid", "failed", "refunded"} and not payment_id:
            raise serializers.ValidationError(
                {"payment_id": "payment_id is required for this payment status."}
            )

        # Prevent going backwards from paid to unpaid.
        if current_status == "paid" and payment_status == "unpaid":
            raise serializers.ValidationError(
                {"payment_status": "Paid orders cannot be set back to unpaid."}
            )

        return attrs

    # Restore stock if the payment is failed
    def update(self, instance, validated_data):
        old_payment_status = instance.payment_status
        new_payment_status = validated_data.get("payment_status", old_payment_status)

        instance = super().update(instance, validated_data)

        if old_payment_status != "failed" and new_payment_status == "failed":
            instance.restore_stock()
        
