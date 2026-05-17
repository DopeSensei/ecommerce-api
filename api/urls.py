from django.urls import path
from . import views

order_list_create = views.OrderViewSet.as_view({
    "get": "list",
    "post": "create",
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

    path("orders/", order_list_create),
    path("orders/<uuid:pk>/", order_detail),
    path("orders/<uuid:pk>/status/", order_set_status),
    path("orders/<uuid:pk>/payment/", order_set_payment),
]
