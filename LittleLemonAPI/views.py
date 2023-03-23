from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response 
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from rest_framework.throttling import UserRateThrottle
from . import models, serializers

# Create your views here.
class CategoriesView(generics.ListCreateAPIView):
    queryset = models.Category.objects.all()
    serializer_class = serializers.CategorySerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    throttle_classes = [UserRateThrottle]
    
class SingleCategoryView(generics.RetrieveUpdateDestroyAPIView):
    queryset = models.Category.objects.all()
    serializer_class = serializers.CategorySerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    throttle_classes = [UserRateThrottle]
    
class MenuItemsView(generics.ListCreateAPIView):
    queryset = models.MenuItem.objects.all()
    serializer_class = serializers.MenuItemSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    throttle_classes = [UserRateThrottle]
    filterset_fields = ['category', 'featured']
    ordering_fields = ['price', 'title']
    search_fields = ['title', 'category__title']
    
class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = models.MenuItem.objects.all()
    serializer_class = serializers.MenuItemSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    throttle_classes = [UserRateThrottle]
       
class GroupUsersView(generics.ListCreateAPIView):
    serializer_class = serializers.UserSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    throttle_classes = [UserRateThrottle]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group = None
    
    def get_queryset(self):
        group_name = self.kwargs['group'].replace('-', ' ')
        self.group = get_object_or_404(models.Group, name=group_name)
        queryset = self.group.user_set.prefetch_related('groups').all()
        return queryset
        
    def list(self, request, *args, **kwargs):
        users = self.get_queryset()
        serializer = serializers.UserSerializer(users, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        serializer = serializers.UserSerializer(data=request.data)
        username = serializer.initial_data['username']
        user_instance = get_object_or_404(models.User, username=username)
        user_instance.groups.add(self.group)
        user_instance.save()
        return Response(serializers.UserSerializer(user_instance).data, status=status.HTTP_201_CREATED)
            
class SingleGroupUserView(generics.DestroyAPIView):
    queryset = models.User.objects.prefetch_related('groups').all()
    serializer_class = serializers.UserSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    throttle_classes = [UserRateThrottle]
    
    def destroy(self, request, *args, **kwargs):
        group_instance = get_object_or_404(models.Group, name=self.kwargs['group'].replace('-', ' '))
        user_instance = get_object_or_404(models.User, pk=self.kwargs['pk'])
        group_instance.user_set.remove(user_instance)
        group_instance.save()
        serializer = serializers.UserSerializer(user_instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CartView(generics.ListCreateAPIView, generics.DestroyAPIView):
    queryset = models.Cart.objects.select_related('menuitem').all()
    serializer_class = serializers.CartSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    
    def get_queryset(self):
        return models.Cart.objects.select_related('menuitem').filter(user=self.request.user).all()
    
    def create(self, request, *args, **kwargs):
        if self.request.user.groups.exists():
            return Response({'message': 'only customers have access'}, status=status.HTTP_403_FORBIDDEN)
        serializer = serializers.CartSerializer(data=request.data)
        if serializer.is_valid():
            menuitem = serializer.validated_data['menuitem']
            quantity = serializer.validated_data['quantity']
            unit_price = menuitem.price
            cart_instance = models.Cart.objects.create(
                user = self.request.user,
                menuitem = menuitem,
                quantity = quantity,
                unit_price = unit_price,
                price = unit_price * quantity
            )
            cart_instance.save()
            return Response(serializers.CartSerializer(cart_instance).data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def destroy(self, request, *args, **kwargs):
        if self.request.user.groups.exists():
            return Response({'message': 'only customers have access'}, status=status.HTTP_403_FORBIDDEN)
        deleted = self.get_queryset().delete()
        return Response(deleted, status=status.HTTP_200_OK)
     
class OrdersView(generics.ListCreateAPIView):
    queryset = models.Order.objects.select_related('user', 'menuitem').all()
    serializer_class = serializers.OrderSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    filterset_fields = ['status', 'date', 'delivery_crew__username']
    ordering_fields = ['date', 'user__username', 'delivery_crew__username']
    search_fields = ['user__username', 'delivery_crew__username']
    
    def list(self, request, *args, **kwargs):
        if not self.request.user.groups.exists():
            order_items = serializers.OrderItemSerializer(
                models.OrderItem.objects.filter(user=self.request.user).all(), many=True
            )
            return Response(order_items.data, status=status.HTTP_200_OK)
        elif self.request.user.groups.filter(name='manager').exists():
            order_items = serializers.OrderItemSerializer(
                models.OrderItem.objects.all(), many=True
            )
            return Response(order_items.data, status=status.HTTP_200_OK)
        elif self.request.user.groups.filter(name='delivery crew').exists():
            order_items = serializers.OrderItemSerializer(
                models.OrderItem.objects.all().filter(delivery_crew=self.request.user), many=True
            )
            return Response(order_items.data, status=status.HTTP_200_OK)
        
    def create_order_item_from_cart(request, *args, **kwargs):
        cart_queryset = models.Cart.objects.filter(user=request.user).iterator()
        for cart_item in cart_queryset:
            order_item = models.OrderItem.objects.create(
                user = request.user,
                menuitem = cart_item.menuitem,
                quantity = cart_item.quantity,
                unit_price = cart_item.unit_price,
                price = cart_item.price
            )
            cart_item.delete()
        
    def create(self, request, *args, **kwargs):
        if self.request.user.groups.exists():
            return Response({'message': 'only customer can create order'}, status=status.HTTP_403_FORBIDDEN)
        else:
            #create an order instance
            order_instance = models.Order.objects.create(
                user=self.request.user
            )
            #translate all cart instances to order item instances
            self.create_order_item_from_cart(self.request)
            return Response(serializers.OrderSerializer(order_instance).data, status=status.HTTP_200_OK)

class SingleOrderView(generics.RetrieveUpdateDestroyAPIView):
    queryset = models.Order.objects.select_related('user').all()
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    serializer_class = serializers.OrderSerializer
    
    def retrieve(self, request, *args, **kwargs):
        if self.request.user.groups.exists():
            return Response({"message":"only customer can access this url"}, status=status.HTTP_403_FORBIDDEN)
        queryset = self.get_queryset().filter(user=self.request.user)
        order_instance = get_object_or_404(queryset, id=self.kwargs['pk'])
        serialized_order_items = serializers.OrderItemSerializer(models.OrderItem.objects.filter(order=order_instance), many=True)
        return Response(serialized_order_items.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        if self.request.user.groups.filter(name='manager').exists():
            order_instance = get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])
            deleted = order_instance.delete()
            return Response(deleted, status=status.HTTP_200_OK)
        else:
            return Response({"message":"only managers have access"}, status=status.HTTP_403_FORBIDDEN)
    
    def update(self, request, *args, **kwargs):
        if not self.request.user.groups.exists():
            return Response({'message':"customers don't have access"}, status=status.HTTP_403_FORBIDDEN)
        elif self.request.user.groups.filter(name='manager').exists():
            serializer = serializers.OrderSerializer(self.request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
        elif self.request.user.groups.filter(name='delivery crew').exists():
            # delivery crew, update the order status only
            if not self.request.data.get('delivery crew', default=None):
                return Response({"message":"delivery crew can only update order status"}, status=status.HTTP_400_BAD_REQUEST)