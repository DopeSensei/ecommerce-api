from django.shortcuts import render
from rest_framework import filters, generics, viewsets
from api.models import User, Product
from api.serializers import UserCreateSerializer, UserReadSerializer, UserUpdateSerializer, ProductSerializer, ProductCreateUpdateSerializer
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
    

# PRODUCT Views

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True).select_related("category")
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

class ProductCreateView(generics.CreateAPIView):
    serializer_class = ProductCreateUpdateSerializer
    permission_classes = [IsAdminUser]

class ProductUpdateView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.select_related("category")
    serializer_class = ProductCreateUpdateSerializer
    permission_classes = [IsAdminUser]