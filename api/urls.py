from django.urls import path
from . import views

urlpatterns = [
    path("users/", views.UserListView.as_view()),
    path("users/register/", views.UserRegisterView.as_view()),
    path("users/me/", views.UserMeUpdateView.as_view()),

    path("products/", views.ProductListView.as_view()),
    path("products/create/", views.ProductCreateView.as_view()),
    path("products/<int:pk>/", views.ProductUpdateView.as_view()),

]