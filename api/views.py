from django.shortcuts import render
from rest_framework import filters, generics, viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.decorators import action
from api.models import User, Product, Category, Order, Cart, CartItem
from api.serializers import (
    UserCreateSerializer, 
    UserReadSerializer, 
    UserUpdateSerializer, 
    ProductSerializer, 
    ProductCreateUpdateSerializer, 
    CategorySerializer,
    OrderReadSerializer,
    OrderCreateSerializer,
    OrderStatusUpdateSerializer,
    OrderPaymentUpdateSerializer,
    CartSerializer,
    CartItemCreateSerializer,
    CartItemReadSerializer,
    CartItemQuantityUpdateSerializer,
    CheckoutSerializer,
)
from api.permissions import IsAnonymous
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated

# Create your views here.

# USER Views

class UserRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [IsAnonymous]

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserReadSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None

class UserMeUpdateView(generics.UpdateAPIView):
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
    

# CATEGORY Views

class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.order_by("name")
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return [AllowAny()]
    
class CategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_url_kwarg = "category_id"

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAdminUser()]
        return [AllowAny()]
    

# PRODUCT Views

class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.filter(is_active=True).select_related("category")

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ProductSerializer
        return ProductCreateUpdateSerializer
    
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return [AllowAny()]
    
class ProductRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.select_related("category")
    lookup_url_kwarg = "product_id"

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ProductSerializer
        return ProductCreateUpdateSerializer
    
    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAdminUser()]
        return [AllowAny()]
    

# CART Views

class CartView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # get_or_create() returns (object, created); "_" means the second value is intentionally unused here.
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart
    

class CartItemAddView(generics.CreateAPIView):
    serializer_class = CartItemCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity}
        )

        # "created" is the boolean returned by get_or_create()
        if not created:
            new_quantity = cart_item.quantity + quantity
            if product.stock < new_quantity:
                return Response(
                    {"quantity": f"Only {product.stock} item(s) available in stock."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            cart_item.quantity = new_quantity
            cart_item.save(update_fields=["quantity"])

        return Response(
            CartSerializer(cart, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class CartItemUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user).select_related("product")

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CartItemReadSerializer
        return CartItemQuantityUpdateSerializer
    

class CheckoutView(generics.GenericAPIView):
    serializer_class = CheckoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(
            OrderReadSerializer(order, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    
# ORDER Views

# Orders are more than a simple CRUD resource; they follow a lifecycle.
# Besides create/list/retrieve, they also require domain-specific actions such as
# status updates and payment updates, so grouping them under a single ViewSet
# keeps the API more consistent and easier to extend.
class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    # select_related joins single-value relations in one query;
    # prefetch_related fetches multi-value/nested relations with extra queries to avoid N+1 lookups.
    queryset = Order.objects.select_related(
        "user", "shipping_address", "billing_address"
    ).prefetch_related("items__product")

    def get_queryset(self):
        # created_at comes from the Order model; newest orders are listed first.
        qs = self.queryset.order_by("-created_at")
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        if self.action == "set_status":
            return OrderStatusUpdateSerializer
        if self.action == "set_payment":
            return OrderPaymentUpdateSerializer
        return OrderReadSerializer

    def get_permissions(self):
        if self.action in {"set_status", "set_payment"}:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    # @action exposes a custom endpoint outside the standard list/retrieve/create actions.
    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        # get_object() is a DRF helper that resolves the current Order from the URL lookup.
        order = self.get_object()
        # get_serializer() instantiates the class returned by get_serializer_class().
        serializer = self.get_serializer(order, data=request.data, partial=True)
        # is_valid() runs serializer validation before saving changes. (built-in)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            # get_serializer_context() passes request/view context into serializers. (built-in)
            OrderReadSerializer(order, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"], url_path="payment")
    def set_payment(self, request, pk=None):
        order = self.get_object()
        serializer = self.get_serializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            OrderReadSerializer(order, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )
