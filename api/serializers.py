from django.db import transaction
from rest_framework import serializers
from .models import Product, Order, OrderItem, User, Address, Cart, CartItem, Category


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


    