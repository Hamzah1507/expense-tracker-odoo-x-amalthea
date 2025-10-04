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
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('company-users/', views.CompanyUsersView.as_view(), name='company-users'),
    path('team-members/', views.ManagerEmployeesView.as_view(), name='team-members'),
    path('assign-manager/', views.assign_manager, name='assign-manager'),
    path('change-role/', views.change_user_role, name='change-role'),
]
