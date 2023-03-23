from django.urls import path
from . import views
urlpatterns = [
    path('categories', views.CategoriesView.as_view(), name='categories'),
    path('categories/<int:pk>', views.SingleCategoryView.as_view(), name='single_category'),
    path('menu-items', views.MenuItemsView.as_view(), name='menu_items'),
    path('menu-items/<int:pk>', views.SingleMenuItemView.as_view(), name='single_menu_item'),
    path('groups/<str:group>/users', views.GroupUsersView.as_view(), name='group_users'),
    path('groups/<str:group>/users/<int:pk>', views.SingleGroupUserView.as_view(), name='single_group_user'),
    path('cart/menu-items', views.CartView.as_view(), name='cart'),
    path('orders', views.OrdersView.as_view(), name='orders'),
    path('orders/<int:pk>', views.SingleOrderView.as_view(), name='single_order'),
]