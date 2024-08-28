from django.urls import path
from .views import SignupView, LoginView,UserSearchView,FriendRequestView,ListFriendsView,ListPendingFriendRequestsView
app_name = 'users'
urlpatterns = [
    path('signup', SignupView.as_view(), name='signup'),
    path('login', LoginView.as_view(), name='login'),
    path('user_search/', UserSearchView.as_view(), name='user_search'),
    path('friend-request', FriendRequestView.as_view(), name='friend_request'),
    path('friends_list', ListFriendsView.as_view(), name='friends_list'),
    path('pending-recieved-requests', ListPendingFriendRequestsView.as_view(), name='pending_requests')
]