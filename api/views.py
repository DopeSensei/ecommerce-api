from django.shortcuts import render
from rest_framework import filters, generics, viewsets
from api.models import User
from api.serializers import UserCreateSerializer, UserReadSerializer, UserUpdateSerializer
from api.permissions import IsAnonymous
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated

# Create your views here.

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