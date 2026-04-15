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


# Represent items inside a user's class
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True) # read_only=True dogru mu?

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product",
            "quantity",
            "added_at"
        )


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


class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("product", "quantity")

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value
    
    def validate(self, attrs):
        product = attrs.get("product")
        quantity = attrs.get("quantity")

        # Cross-field validation: only active products with sufficient stock can be added to an order.
        if product is not None and not product.is_active:
            raise serializers.ValidationError({"product": "This product is inactive."})
        
        if product is not None and quantity is not None and product.stock < quantity:
            raise serializers.ValidationError(
                {"quantity": f"Only {product.stock} item(s) available in stock."}
            )

        return attrs


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
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = (
            "order_id",
            "shipping_address",
            "billing_address",
            "items",
            "status",
            "payment_status",
            "payment_id",
            "total_price",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "order_id",
            "status",
            "payment_status",
            "payment_id",
            "total_price",
            "created_at",
            "updated_at",
        )

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must contain at least one item.")
        return value
    

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None

        shipping_address = attrs.get("shipping_address")
        billing_address = attrs.get("billing_address")

        # If user in authenticated, addresses must belong to that user.
        if user:
            if shipping_address and shipping_address.user_id != user.id:
                raise serializers.ValidationError(
                    {"shipping_address": "You can only use your own shipping address."}
                )
            if billing_address and billing_address.user_id != user.id:
                raise serializers.ValidationError(
                    {"billing_address": "You can only use your own billing address."}
                )
            
        return attrs

    
    def create(self, validated_data):
        items_data = validated_data.pop("items") # Remove nested items before creating Order; items belong to OrderItem rows.
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None

        with transaction.atomic(): # Ensure order + order items are saved atomically (all-or-nothing).
            order = Order.objects.create(user=user, **validated_data)

            for item in items_data:
                product = item["product"]
                quantity = item["quantity"]

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price_at_purchase=product.get_effective_price(),
                )

            order.calculate_total()
        
        return order


# Admin
class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("status",)

    def validate_status(self, value):
        current_status = self.instance.status if self.instance else None

        locked_statuses = {Order.StatusChoices.DELIVERED}
        if current_status in locked_statuses and value != current_status:
            raise serializers.ValidationError("Finalized orders cannot change status.")

        return value        


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
        


