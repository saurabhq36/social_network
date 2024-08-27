from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from rest_framework import generics, permissions
from .pagination import UserSearchPagination
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from .models import FriendRequest, Friendship
from .serializers import UserSerializer,FriendRequestSerializer
from django.utils.timezone import now
from datetime import timedelta



    

class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')

        if not email or not password or not first_name or not last_name:
            return Response({'error': 'Email, password, first name, and last name are required'}, status=status.HTTP_400_BAD_REQUEST)

        email = email.lower()

        try:
            validate_email(email)
        except ValidationError:
            return Response({'error': 'Invalid email format'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email is already in use'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        token = Token.objects.create(user=user)
        return Response({'token': token.key}, status=status.HTTP_201_CREATED)






class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        email = email.lower()

        user = authenticate(request, username=email, password=password)
        if user is not None:
            return Response({'message': 'Signup successful'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        





class UserSearchView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = UserSearchPagination
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        search_keyword = request.query_params.get('search', '').lower()
        if not search_keyword:
            return Response({'error': 'No search keyword provided'}, status=status.HTTP_400_BAD_REQUEST)

        if '@' in search_keyword:
            users = User.objects.filter(email__iexact=search_keyword)
        else:
            users = User.objects.filter(first_name__icontains=search_keyword) | User.objects.filter(last_name__icontains=search_keyword)

        if not users.exists():
            return Response({'error': 'No users found matching the search criteria'}, status=status.HTTP_404_NOT_FOUND)

        users = users.order_by('-date_joined')

        serializer = self.get_serializer(users, many=True)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(users, request, view=self)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)


class FriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        action = request.data.get('action')
        target_email = request.data.get('email')
        user = request.user
        
        if not action or not target_email:
            return Response({'error': 'Action and email are required'}, status=status.HTTP_400_BAD_REQUEST)

        target_user = User.objects.filter(email=target_email).first()
        if not target_user:
            return Response({'error': 'Target user not found'}, status=status.HTTP_404_NOT_FOUND)

        if user == target_user:
            return Response({'error': 'You cannot send, accept, or reject a friend request to yourself'}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'send':
            # Key for tracking request count
            request_key = f"friend_request_count_{user.id}"
            request_count = cache.get(request_key, 0)
            request_time_key = f"friend_request_time_{user.id}"
            last_request_time = cache.get(request_time_key)

            if last_request_time and now() - last_request_time < timedelta(minutes=1):
                if request_count >= 3:
                    return Response({'error': 'Request limit exceeded. You can only send 3 requests per minute.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            else:
                # Reset request count and time if more than a minute has passed
                request_count = 0
                cache.set(request_time_key, now(), timeout=60)

            # Check for existing friend requests
            existing_request = FriendRequest.objects.filter(
                from_user=user, to_user=target_user
            ).first() or FriendRequest.objects.filter(
                from_user=target_user, to_user=user
            ).first()

            if existing_request:
                if existing_request.status == 'pending':
                    return Response({'info': 'A friend request is already pending between these users'}, status=status.HTTP_400_BAD_REQUEST)
                elif existing_request.status == 'accepted':
                    return Response({'info': 'A friend request has already been accepted between these users'}, status=status.HTTP_400_BAD_REQUEST)

            # Create new friend request
            FriendRequest.objects.create(from_user=user, to_user=target_user)

            # Update request count and store it in the cache
            cache.set(request_key, request_count + 1, timeout=60)

            return Response({'status': 'Friend request sent'}, status=status.HTTP_200_OK)

        elif action == 'accept':
            request = FriendRequest.objects.filter(from_user=target_user, to_user=user, status='pending').first()
            if not request:
                return Response({'error': 'No pending request found'}, status=status.HTTP_400_BAD_REQUEST)
            request.status = 'accepted'
            request.save()
            Friendship.objects.get_or_create(user1=user, user2=target_user)
            return Response({'status': 'Friend request accepted'}, status=status.HTTP_200_OK)

        elif action == 'reject':
            request = FriendRequest.objects.filter(from_user=target_user, to_user=user, status='pending').first()
            if not request:
                return Response({'error': 'No pending request found'}, status=status.HTTP_400_BAD_REQUEST)
            request.status = 'rejected'
            request.save()
            return Response({'status': 'Friend request rejected'}, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)





class ListFriendsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        
        friendships_as_user1 = Friendship.objects.filter(user1=user)
        friendships_as_user2 = Friendship.objects.filter(user2=user)
        
        # Extract friends from both queries
        friends = []
        for friendship in friendships_as_user1:
            friends.append(friendship.user2)
        for friendship in friendships_as_user2:
            friends.append(friendship.user1)
        
        friends = list(set(friends))
        
        # Get the user objects from the list of friend IDs
        friends = User.objects.filter(id__in=[friend.id for friend in friends]).order_by('-date_joined')
        
        # Serialize and return the friends
        serializer = UserSerializer(friends, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class ListPendingFriendRequestsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return FriendRequest.objects.filter(to_user=user, status='pending').order_by('-created_at')
    
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = FriendRequestSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
