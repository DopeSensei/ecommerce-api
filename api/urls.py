from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

order_list = views.OrderViewSet.as_view({
    "get": "list",
})

order_detail = views.OrderViewSet.as_view({
    "get": "retrieve",
})

order_set_status = views.OrderViewSet.as_view({
    "patch": "set_status",
})

order_set_payment = views.OrderViewSet.as_view({
    "patch": "set_payment",
})


urlpatterns = [
    path("users/", views.UserListView.as_view()),
    path("users/register/", views.UserRegisterView.as_view()),
    path("users/me/", views.UserMeUpdateView.as_view()),

    path("products/", views.ProductListCreateView.as_view()),
    path("products/<int:product_id>/", views.ProductRetrieveUpdateDestroyView.as_view()),

    path("categories/", views.CategoryListCreateView.as_view()),
    path("categories/<int:category_id>/", views.CategoryRetrieveUpdateDestroyView.as_view()),

    path("cart/", views.CartView.as_view()),
    path("cart/items/", views.CartItemAddView.as_view()),
    path("cart/items/<int:pk>/", views.CartItemUpdateDeleteView.as_view()),
    path("checkout/", views.CheckoutView.as_view()),

    path("orders/", order_list),
    path("orders/<uuid:pk>/", order_detail),
    path("orders/<uuid:pk>/status/", order_set_status),
    path("orders/<uuid:pk>/payment/", order_set_payment),

    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]
