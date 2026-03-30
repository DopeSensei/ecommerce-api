from django.urls import path
from . import views

urlpatterns = [
    path("users/", views.UserListView.as_view()),
    path("users/register/", views.UserRegisterView.as_view()),
    path("users/me/", views.UserMeUpdateView.as_view()),

    path("products/", views.ProductListCreateView.as_view()),
    path("products/<int:pk>/", views.ProductRetrieveUpdateDestroyView.as_view()),
]