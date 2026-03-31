from django.urls import path
from . import views

urlpatterns = [
    path("users/", views.UserListView.as_view()),
    path("users/register/", views.UserRegisterView.as_view()),
    path("users/me/", views.UserMeUpdateView.as_view()),

    path("products/", views.ProductListCreateView.as_view()),
    path("products/<int:product_id>/", views.ProductRetrieveUpdateDestroyView.as_view()),

    path("categories/", views.CategoryListCreateView.as_view()),
    path("categories/<int:category_id>/", views.CategoryRetrieveUpdateDestroyView.as_view())
]