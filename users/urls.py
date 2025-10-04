from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserListView, basename='user')
router.register(r'user-detail', views.UserDetailView, basename='user-detail')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    # ... other paths
]