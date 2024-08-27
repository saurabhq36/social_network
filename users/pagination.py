from rest_framework.pagination import PageNumberPagination

class UserSearchPagination(PageNumberPagination):
    page_size = 10  # Number of records per page
    page_size_query_param = 'page_size'
    max_page_size = 100  # Maximum page size limit