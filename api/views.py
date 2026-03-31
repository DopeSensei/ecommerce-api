from django.shortcuts import render
from rest_framework import filters, generics, viewsets
from api.models import User, Product, Category
from api.serializers import UserCreateSerializer, UserReadSerializer, UserUpdateSerializer, ProductSerializer, ProductCreateUpdateSerializer, CategorySerializer
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