from rest_framework import serializers
from . import models
import bleach

class GroupSerializer(serializers.ModelSerializer):
    def validate_name(self, value):
        return bleach.clean(value)
    class Meta:
        model = models.Group
        fields = ['id', 'name']

class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True)
    def validate_username(self, value):
        return bleach.clean(value)
    class Meta:
        model = models.User
        fields = ['id', 'username', 'email', 'groups', 'date_joined', 'is_staff', 'is_active']
        read_only_fields = ['email', 'date_joined', 'is_staff', 'is_active']
        
class CategorySerializer(serializers.ModelSerializer):
    def validate_title(self, value):
        return bleach.clean(value)
    class Meta:
        model = models.Category
        fields = ['id','slug','title']

class MenuItemSerializer(serializers.ModelSerializer):
    category = CategorySerializer
    def validate_title(self, value):
        return bleach.clean(value)
    class Meta:
        model = models.MenuItem
        fields = ['id','title','price','featured','category']
        
class CartSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    menuitem = MenuItemSerializer
    class Meta:
        model = models.Cart
        fields = ['id', 'user', 'menuitem', 'quantity', 'unit_price', 'price']
        read_only_fields = ['unit_price', 'price']

class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer
    class Meta:
        model = models.Order
        fields = ['id', 'user', 'delivery_crew', 'status', 'total', 'date']
        read_only_fields = ['user', 'total', 'date']
        
class OrderItemSerializer(serializers.ModelSerializer):
    order = OrderSerializer
    menuitem = MenuItemSerializer
    class Meta:
        model = models.OrderItem
        fields = ['id', 'order', 'menuitem', 'quantity', 'unit_price', 'price']
        read_only_fields = ['order', 'menuitem', 'quantity', 'unit_price', 'price']