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
    """
    API endpoint for searching users by first name, last name, or email.

    This view allows authenticated users to search for other users in the system.
    The search can be performed using a keyword, which can be either a part of the
    first name, last name, or the exact email address of the user.

    Pagination is applied to the search results to limit the number of users returned in a single response.

    Attributes:
        permission_classes (list): Specifies that only authenticated users can access this view.
        pagination_class (class): Defines the pagination class used to paginate the search results.
        serializer_class (class): Specifies the serializer class used to serialize the user data.

    Methods:
        get(self, request, *args, **kwargs):
            Handles GET requests to search for users based on the provided keyword.

            Input:
                - request (Request): The HTTP request object. The `search` keyword is expected in the query parameters.

            Output:
                - If the search keyword is missing:
                    - Returns a JSON response with an error message and a 400 HTTP status.
                - If no users are found matching the search criteria:
                    - Returns a JSON response with an error message and a 404 HTTP status.
                - If users are found:
                    - Returns a paginated JSON response containing the serialized user data and a 200 HTTP status.
    """
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
    """
    API endpoint for managing friend requests.

    This view allows authenticated users to send, accept, or reject friend requests
    to other users. The actions are determined based on the 'action' parameter sent
    in the request body.

    Attributes:
        permission_classes (list): Specifies that only authenticated users can access this view.

    Methods:
        post(self, request):
            Handles POST requests to manage friend requests.

            Input:
                - request (Request): The HTTP request object containing the following data in the body:
                    - action (str): The action to perform, which can be 'send', 'accept', or 'reject'.
                    - target_email (str): The email of the user to whom the friend request is being sent, accepted, or rejected.

            Output:
                - If 'action' or 'target_email' is missing:
                    - Returns a JSON response with an error message and a 400 HTTP status.
                - If the target user is not found:
                    - Returns a JSON response with an error message and a 404 HTTP status.
                - If the user attempts to send a friend request to themselves:
                    - Returns a JSON response with an error message and a 400 HTTP status.

                - If 'send' action is chosen:
                    - If the user has already sent 3 requests within the last minute:
                        - Returns a JSON response with an error message and a 429 HTTP status.
                    - If there is an existing pending or accepted friend request:
                        - Returns a JSON response with an appropriate message and a 400 HTTP status.
                    - If no issues are found:
                        - Creates a new friend request, updates the request count, and returns a JSON response with a 200 HTTP status.

                - If 'accept' action is chosen:
                    - If there is no pending request from the target user:
                        - Returns a JSON response with an error message and a 400 HTTP status.
                    - If a pending request is found:
                        - Accepts the request, creates a friendship, and returns a JSON response with a 200 HTTP status.

                - If 'reject' action is chosen:
                    - If there is no pending request from the target user:
                        - Returns a JSON response with an error message and a 400 HTTP status.
                    - If a pending request is found:
                        - Rejects the request and returns a JSON response with a 200 HTTP status.

                - If an invalid action is provided:
                    - Returns a JSON response with an error message and a 400 HTTP status.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        action = request.data.get('action')
        target_email = request.data.get('target_email')
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
    """
    API endpoint to list all friends of the authenticated user.

    This view retrieves the list of friends for the authenticated user by checking both
    sides of the Friendship relationship (i.e., where the user is either user1 or user2).
    The friends are then returned in descending order based on the date they joined.

    Attributes:
        permission_classes (list): Specifies that only authenticated users can access this view.

    Methods:
        get(self, request, *args, **kwargs):
            Handles GET requests to list the friends of the authenticated user.

            Input:
                - request (Request): The HTTP request object that contains user authentication.

            Output:
                - If the user has no friends:
                    - Returns a JSON response with the message "No friends yet" and a 200 HTTP status.
                - If the user has friends:
                    - Returns a serialized list of friends, ordered by the date they joined, and a 200 HTTP status.
    """
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
        if not serializer.data:
            return Response({"message": "No friends yet"}, status=status.HTTP_200_OK)
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
